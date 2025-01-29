-- ftml - enable SILE to process FTML (font test markup language)
-- copyright 2016-2019 SIL Global and released under the MIT/X11 license
-- NB: some commands referenced here are defined in ftml.sil

local ftml = SILE.baseClass { id = "ftml" }

SILE.require("packages/counters")
SILE.require("packages/bidi")
SILE.require("packages/rules")
SILE.require("packages/color")
SILE.require("packages/rebox")
local icu = require("justenoughicu")

-- SILE's -e command line option can be used to specify the font(s) to test:
-- -e "SILE.scratch.ftmlfontlist={'Andika New Basic Italic','Andika New Basic Bold'}"
-- If the font string has a ".", it is assumed to be a file name, otherwise the name of an installed font.
SU.debug("ftml", "font list loaded into SILE.scratch.ftmlfontlist: " .. SILE.scratch.ftmlfontlist)
-- Note: can't use the normal SILE.scratch.ftml.xxx namespace
-- because, when the command line is being read, the ftml class
-- hasn't yet been processed, so SILE.scratch.ftml has not yet been created.

SILE.scratch.ftml = {}
SILE.scratch.ftml = { head = {}, fontlist = {}, testgroup = {} }

function dump(o, i)
   if type(o) == 'table' then
      local s = '\n'.. i .. '{ '
      for k,v in pairs(o) do
         if type(k) ~= 'number' then k = '"'..k..'"' end
         s = s ..k..': ' .. dump(v, '  '..i) .. ','
      end
      return s .. '}'
   else
      return tostring(o)
   end
end

ftml:declareFrame("content", {
    left = "5%pw",
    right = "95%pw",
    top = "5%ph",
    bottom = "95%ph"
  })
ftml.pageTemplate.firstContentFrame = ftml.pageTemplate.frames["content"]

function ftml:init()
  SILE.settings.set("document.parindent",SILE.nodefactory.glue())
  SILE.settings.set("document.baselineskip",SILE.nodefactory.vglue("1.2em"))
  SILE.settings.set("document.parskip",SILE.nodefactory.vglue("0pt"))
  SILE.settings.set("document.spaceskip")
  return SILE.baseClass:init()
end

-- copied from plain class
SILE.registerCommand("vfill", function (options, content)
  SILE.typesetter:leaveHmode()
  SILE.typesetter:pushExplicitVglue(SILE.nodefactory.vfillglue())
end, "Add huge vertical glue")

local reverse_each_node = function (nodelist)
  for j = 1, #nodelist do
    if nodelist[j].type =="hbox" then
      if nodelist[j].value.items then SU.flip_in_place(nodelist[j].value.items) end
      SU.flip_in_place(nodelist[j].value.glyphString)
    end
  end
end

local nodeListToText = function (nl)
  local owners, text = {}, {}
  local p = 1
  for i = 1, #nl do local n = nl[i]
    if n.text then
      local utfchars = SU.splitUtf8(n.text)
      for j = 1, #utfchars do
        owners[p] = { node = n, pos = j }
        text[p] = utfchars[j]
        p = p + 1
      end
    else
      owners[p] = { node = n }
      text[p] = SU.utf8char(0xFFFC)
      p = p + 1
    end
  end
  return owners, text
end

local splitNodeAtPos = function (n, splitstart, p)
  if n.is_unshaped then
    local utf8chars = SU.splitUtf8(n.text)
    local n2 = SILE.nodefactory.unshaped({ text = "", options = pl.tablex.copy(n.options) })
    local n1 = SILE.nodefactory.unshaped({ text = "", options = pl.tablex.copy(n.options) })
    for i = splitstart, #utf8chars do
      if i <= p then n1.text = n1.text .. utf8chars[i]
      else n2.text = n2.text .. utf8chars[i]
      end
    end
    return n1, n2
  else
    SU.error("Unsure how to split node "..n.." at position "..p, true)
  end
end

local splitNodelistIntoBidiRuns = function (self)
  local nl = self.state.nodes
  if #nl == 0 then return nl end
  local owners, text = nodeListToText(nl)
  local base_level = self.frame:writingDirection() == "RTL" and 1 or 0
  local runs = { icu.bidi_runs(table.concat(text), self.frame:writingDirection()) }
  if #owners ~= runs.length then
    SU.debug("ftml", "Runs: " .. runs .. ". Owners: " .. owners)
  end
  table.sort(runs, function (a, b) return a.start < b.start end)
  -- local newNl = {}
  -- Split nodes on run boundaries
  for i = 1, #runs do
    local run = runs[i]
    if run.run then -- Work around sile issue #839
        local t = SU.splitUtf8(run.run)
        run.length = #t
    end
    local thisOwner = owners[run.start+run.length]
    local nextOwner = owners[run.start+1+run.length]
    -- print(thisOwner, nextOwner)
    if nextOwner and thisOwner.node == nextOwner.node then
      local before, after = splitNodeAtPos(nextOwner.node, 1, nextOwner.pos-1)
      -- print(before, after)
      local start = nil
      for j = run.start+1, run.start+run.length do
        if owners[j].node==nextOwner.node then
          if not start then start = j end
          owners[j]={ node=before ,pos=j-start+1 }
        end
      end
      for j = run.start + 1 + run.length, #owners do
        if owners[j].node==nextOwner.node then
          owners[j] = { node = after, pos = j - (run.start + run.length) }
        end
      end
    end
  end
  -- Assign direction/level to nodes
  for i = 1, #runs do
    local runstart = runs[i].start+1
    local runend   = runstart + runs[i].length-1
    for j = runstart, runend do
      if not owners[j] then
        SU.debug("ftml", "i = " .. i .. ", j = " .. j .. " Run: " .. runs .. ". Owners: " .. owners)
      end
      if owners[j].node and owners[j].node.options then
        owners[j].node.options.direction = runs[i].dir
        owners[j].node.options.bidilevel = runs[i].level - base_level
      end
    end
  end
  -- String together nodelist
  nl={}
  for i = 1, #owners do
    if #nl and nl[#nl] ~= owners[i].node then
      nl[#nl+1] = owners[i].node
      -- print(nl[#nl], nl[#nl].options)
    end
  end
  -- for i = 1, #nl do print(i, nl[i]) end
  return nl
end

SILE.registerCommand("hbox", function (options, content)
SU.debug("ftml", "entering hbox")
SU.debug("ftml", "options:")
SU.debug("ftml", options)
SU.debug("ftml", "content:")
-- SU.debug("ftml", content)
  local index = #(SILE.typesetter.state.nodes)+1
  local recentContribution = {}
  SILE.process(content)
  local l = SILE.length()
  local h,d = 0,0
  local dir = SILE.scratch.ftml.rtl and "RTL" or "LTR" -- SILE.typesetter.frame.direction
  SU.debug("ftml", "hbox direction: " .. dir .. " font direction: " .. SILE.settings.get("font.direction") .. " ftml rtl: " .. SILE.scratch.ftml.rtl)
  -- if SILE.scratch.ftml.rtl then
    newnodes = splitNodelistIntoBidiRuns(SILE.typesetter)
    SILE.typesetter.state.nodes = newnodes
  -- end
  for i = index, #(SILE.typesetter.state.nodes) do
    local node = SILE.typesetter.state.nodes[i]
    if node.is_unshaped then
SU.debug("ftml", "node options "..node.options)
      local s = node:shape()
      for i = 1, #s do
        n = s[i].nodes
        if n then
          for j = 1, #n do
            SU.debug("ftml", "subnode options "..n[j].value.options)
            if n[j].value and n[j].value.options and n[j].value.options.direction == "RTL" then
              if n[j].value.items then SU.flip_in_place(n[j].value.items) end
              SU.flip_in_place(n[j].value.glyphString)
            end
          end
        end
        recentContribution[#recentContribution+1] = s[i]
SU.debug("ftml", "node contribution: " .. dump(s[i], ''))
        h = s[i].height > h and s[i].height or h
        d = s[i].depth > d and s[i].depth or d
        l = l + s[i]:lineContribution()
      end
    else
      recentContribution[#recentContribution+1] = node
      l = l + node:lineContribution()
SU.debug("ftml", "node:lineContribution() = " .. tostring(node:lineContribution()) )
SU.debug("ftml", "node.height = " .. tostring(node.height) )
SU.debug("ftml", "h = " .. tostring(h) )
      h = node.height > h and node.height or h
      d = node.depth > d and node.depth or d
    end
    SILE.typesetter.state.nodes[i] = nil
  end
SU.debug("ftml", "width: " .. l)
  local hbox = SILE.nodefactory.hbox({
    height = h,
    width = l,      -- this gets overriddent to give fixed width box
    textwidth = l,  -- actual text width for right alignment shifting
    depth = d,
    direction = dir,
    value = recentContribution,
    outputYourself = function (self, typesetter, line)
      -- Yuck!
      if self.direction == "RTL" then
       SU.debug("ftml", "Advance by: "..self.width - self.textwidth)
       typesetter.frame:advanceWritingDirection(self.width - self.textwidth)
      end
      local X = typesetter.frame.state.cursorX
      SILE.outputter:setCursor(typesetter.frame.state.cursorX, typesetter.frame.state.cursorY)
      for i = 1, #(self.value) do local node = self.value[i]
        node:outputYourself(typesetter, line)
      end
      typesetter.frame.state.cursorX = X
      if self.direction ~= "RTL" then
        typesetter.frame:advanceWritingDirection(self.width)
      else
        typesetter.frame:advanceWritingDirection(self.textwidth)
      end
      if SU.debugging("hboxes") then SILE.outputter:debugHbox(self, self:scaledWidth(line)) end
    end
  })
  -- table.insert(SILE.typesetter.state.nodes, hbox)
  return hbox
end, "Compiles all the enclosed horizontal-mode material into a single hbox")

SILE.registerCommand("ragged", function (options, content)
  SILE.settings.temporarily(function ()
    if options.left then SILE.settings.set("document.lskip", SILE.nodefactory.hfillglue()) end
    if options.right then SILE.settings.set("document.rskip", SILE.nodefactory.hfillglue()) end
    SILE.settings.set("typesetter.parfillskip", SILE.nodefactory.glue())
    SILE.settings.set("document.parindent", SILE.nodefactory.glue())
    SILE.settings.set("document.baselineskip",SILE.nodefactory.vglue("1.2em"))
    local space = SILE.length("1spc")
    space.stretch = 0
    space.shrink = 0
    SILE.settings.set("document.spaceskip", space)
    SILE.process(content)
    SILE.call("par")
  end)
end)

local function parsefontname(s)
  local num = 0
  s,num = string.gsub(s,"%s*Regular%s*$","")
  local reg = num == 1
  s,num = string.gsub(s,"%s*Italic%s*$","")
  local italic = num == 1
  s,num = string.gsub(s,"%s*Bold%s*$","")
  local bold = num == 1
  s,num = string.gsub(s,"%s+$","")
  s,num = string.gsub(s,"^%s+","")
  return s, reg, bold, italic
end

if SILE.scratch.ftmlfontlist and #SILE.scratch.ftmlfontlist > 0 then -- obtain font info from command line
  SILE.scratch.ftml.numfonts = #SILE.scratch.ftmlfontlist
  for i=1,SILE.scratch.ftml.numfonts do
    local fontspec = SILE.scratch.ftmlfontlist[i]
    SILE.scratch.ftml.fontlist[i] = {}
    if string.find(fontspec,"%.") then -- if . in string, must be filename
      SILE.scratch.ftml.fontlist[i].filename = fontspec
      SILE.scratch.ftml.fontlist[i].family = nil
    else -- must be font family name +- Bold +- Italic +- Regular
      local f, regular, bold, italic = parsefontname(fontspec)
      SILE.scratch.ftml.fontlist[i].filename = nil
      SILE.scratch.ftml.fontlist[i].family = f
      SILE.scratch.ftml.fontlist[i].bold = bold
      SILE.scratch.ftml.fontlist[i].italic = italic
      if (bold or italic) and regular then
        SU.debug("ftml", "Warning: Font specification has Regular as well as Bold or Italic")
        SILE.scratch.ftml.fontlist[i].bold = nil
        SILE.scratch.ftml.fontlist[i].italic = nil
      end
    end
  end
else -- get font info from fontsrc element (which hasn't yet been read)
  SILE.scratch.ftml.numfonts = 0 -- indicates that fontsrc needs to be used
  SU.debug("ftml", "Warning: No valid font specification on command line, fallback to fontsrc element")
end

local function getfeats(fs)
  local start = 0
  local finish, feature, value, pref, suff
  local featuretable = {}
  while start do
    start = start + 1
    start, finish, feature, value = string.find(fs, "^%s*'([^']+)'%s*(%d+)%s*,?%s*", start)
    if start then
      start = finish
      if value == "0" then
        pref = "-"
        suff = ""
      else
        pref = "+"
        suff = "=" .. tostring(value)
      end
      table.insert(featuretable, pref .. feature .. suff)
    end
  end
  return table.concat(featuretable, ",")
end

SILE.registerCommand("style", function (options, content)
  local name = options["name"]
  local feats = options["feats"]
  if feats then
    feats = getfeats(feats)
  else
    feats = ""
  end
  local lang = options["lang"] or ""
  SU.debug("ftml", "style element found: " .. name .. "/" .. feats .. "/" .. lang)
-- if name and name ~= "" then
  SILE.scratch.ftml.head.styles[name] = {feats = feats, lang = lang}
-- else
-- raise error/warning if name is missing
-- end
end)

SILE.registerCommand("head", function (options, content)
SU.debug("ftml", "head1")
  SILE.scratch.ftml.rtl = false
  for j=1,#(_G.arg) do
    if _G.arg[j] == "-r" then
      SILE.scratch.ftml.rtl = true
    elseif _G.arg[j] == "-s" then
      SILE.scratch.ftml.scale = _G.arg[j+1]
      j = j + 1
    end
  end
  -- print ("Command line direction rtl: ".. SILE.scratch.ftml.rtl)
  local head_comment = SILE.findInTree(content, "comment")
  if head_comment then SILE.scratch.ftml.head.comment = head_comment[1] end
  local head_fontscale = SILE.findInTree(content, "fontscale")
  if head_fontscale then 
    SILE.scratch.ftml.head.fontscale = head_fontscale[1]
  else
    SILE.scratch.ftml.head.fontscale = "150"
  end
  if SILE.scratch.ftml.scale then SILE.scratch.ftml.head.fontscale = SILE.scratch.ftml.scale end
  SILE.scratch.ftml.fontsize = math.floor(12*tonumber(SILE.scratch.ftml.head.fontscale)/50)/2.0
SU.debug("ftml", "head2")
  local head_fontsrc = SILE.findInTree(content, "fontsrc")
  if head_fontsrc then SILE.scratch.ftml.head.fontsrc = head_fontsrc[1] end
  local head_title = SILE.findInTree(content, "title")
SU.debug("ftml", "head3")
  if head_title then SILE.scratch.ftml.head.title = head_title[1] end
  local head_styles = SILE.findInTree(content, "styles")
  if head_styles then
    SILE.scratch.ftml.head.styles = {}
    SILE.process(head_styles) -- process the "style" elements contained in this "styles" element
SU.debug("ftml", "head4")
  end
  local head_widths = SILE.findInTree(content, "widths")
  SILE.scratch.ftml.head.widths = {}
  if head_widths then -- perhaps else clause to set defaults if no widths element?
    for k,v in pairs(head_widths["options"]) do
      if type(k) ~= "number" then
        SILE.scratch.ftml.head.widths[k] = v
      end
    end
  end

--[[
At this point 
  SILE.scratch.ftml.head.comment      contains comment text
  SILE.scratch.ftml.head.fontscale    contains fontscale text
  SILE.scratch.ftml.head.fontsrc      contains fontsrc text
  SILE.scratch.ftml.head.title        contains title text
  SILE.scratch.ftml.head.widths       contains a table with any or all of: .table, .label, .string, .stylename, .comment
  SILE.scratch.ftml.head.styles       contains a table with style info, indexed by stylename, which returns a table with keys "feats" and/or "lang"
--]]
-- begin debugging info
  if SILE.scratch.ftml.head.comment then SU.debug("ftml", "comment: " .. SILE.scratch.ftml.head.comment) end
  if SILE.scratch.ftml.head.fontscale then SU.debug("ftml", "fontscale: " .. SILE.scratch.ftml.head.fontscale) end
  if SILE.scratch.ftml.head.fontsrc then SU.debug("ftml", "fontsrc: " .. SILE.scratch.ftml.head.fontsrc) end
  if SILE.scratch.ftml.head.title then SU.debug("ftml", "title: " .. SILE.scratch.ftml.head.title) end
  if SILE.scratch.ftml.head.widths then 
    for k,v in pairs(SILE.scratch.ftml.head.widths) do
      SU.debug("ftml", k .. "=" .. v )
    end
  end
-- end debugging info

  if SILE.scratch.ftml.numfonts == 0 then -- get font from SILE.scratch.ftml.head.fontsrc
    SILE.scratch.ftml.numfonts = 1
    local fontspec = string.match(SILE.scratch.ftml.head.fontsrc,"^%s*local%((.+)%)")
    -- the above doesn't deal with possibility that fontspec has opening/closing quote/apostrophe pair inside parentheses
    -- for example: local("Gentium")
    if fontspec then
      local f, regular, bold, italic = parsefontname(fontspec)
      SILE.scratch.ftml.fontlist[1] = {}
      SILE.scratch.ftml.fontlist[1].filename = nil
      SILE.scratch.ftml.fontlist[1].family = f
      SILE.scratch.ftml.fontlist[1].bold = bold
      SILE.scratch.ftml.fontlist[1].italic = italic
      if (bold or italic) and regular then
        SU.debug("ftml", "Warning: Font specification has Regular as well as Bold or Italic")
        SILE.scratch.ftml.fontlist[1].bold = nil
        SILE.scratch.ftml.fontlist[1].italic = nil
      end
    else
      fontspec = string.match(SILE.scratch.ftml.head.fontsrc,"^%s*url%((.+)%)")
      if fontspec then
        SILE.scratch.ftml.fontlist[1].filename = fontspec
        SILE.scratch.ftml.fontlist[1].family = nil
      else
        SU.debug("ftml", "No font(s) on command line, nor in fontsrc element: " .. SILE.scratch.ftml.head.fontsrc) 
        SU.error("No valid font specification in fontsrc element")
      end
    end
  end

  local labelwidthstr = SILE.scratch.ftml.head.widths.label or "0%"
  local stringwidthstr = SILE.scratch.ftml.head.widths.string or "50%"
  local stylenamewidthstr = SILE.scratch.ftml.head.widths.stylename or "0%"
  local commentwidthstr = SILE.scratch.ftml.head.widths.comment or "0%"

  local labelwidth = tonumber(string.match(labelwidthstr, "%d+"))
  local stringwidth = tonumber(string.match(stringwidthstr, "%d+"))
  local stylenamewidth = tonumber(string.match(stylenamewidthstr, "%d+"))
  local commentwidth = tonumber(string.match(commentwidthstr, "%d+"))
  local gutterwidth = 1

  gutters = SILE.scratch.ftml.numfonts - 1
  if labelwidth > 0 then gutters = gutters + 1 end
  if stylenamewidth > 0 then gutters = gutters + 1 end
  if commentwidth > 0 then gutters = gutters + 1 end
  totalwidth = gutters + labelwidth + (stringwidth * SILE.scratch.ftml.numfonts) + stylenamewidth + commentwidth

  tablewidthstr = SILE.scratch.ftml.head.widths.table or "100%"
  tablewidth = tonumber(string.match(tablewidthstr, "%d+"))
  if tablewidth > 100 or tablewidth < 10 then tablewidth = 100 end
  tablewidth = SILE.measurement(tostring(tablewidth) .. "%fw"):tonumber()

  labelwidth = math.floor(tablewidth*labelwidth/totalwidth)
  stringwidth = math.floor(tablewidth*stringwidth/totalwidth)
  stylenamewidth = math.floor(tablewidth*stylenamewidth/totalwidth)
  commentwidth = math.floor(tablewidth*commentwidth/totalwidth)
  gutterwidth = math.floor(tablewidth*1/totalwidth)

---[[
  SU.debug("ftml", tostring(tablewidth))
  SU.debug("ftml", tostring(labelwidth))
  SU.debug("ftml", tostring(stringwidth))
  SU.debug("ftml", tostring(stylenamewidth))
  SU.debug("ftml", tostring(commentwidth))
  SU.debug("ftml", tostring(gutterwidth))
  if SILE.scratch.ftml.head.styles then 
    for k,v in pairs(SILE.scratch.ftml.head.styles) do
      SU.debug("ftml", k .. "=" .. v)
    end
  end
--]]

  colinfo = {}
  if labelwidth > 0 then
    table.insert(colinfo, {name = "label", width = labelwidth })
    table.insert(colinfo, {name = "gutter", width = gutterwidth })
  end
  if stringwidth > 0 then
    for fontcount = 1, SILE.scratch.ftml.numfonts do
      local stringindex = "string" .. tostring(fontcount)
      table.insert(colinfo, {name = stringindex, width = stringwidth})
      table.insert(colinfo, {name = "gutter", width = gutterwidth })
    end
  else
    SU.error("String element has no defined width!")
  end
  if stylenamewidth > 0 then
    table.insert(colinfo, {name = "stylename", width = stylenamewidth })
    table.insert(colinfo, {name = "gutter", width = gutterwidth })
  end
  if commentwidth > 0 then
    table.insert(colinfo, {name = "comment", width = commentwidth })
    table.insert(colinfo, {name = "gutter", width = gutterwidth })
  end
  colinfo[#colinfo] = nil -- Drop final gutter

  SILE.scratch.ftml.tablecolumns = colinfo
  SU.debug("ftml", "table columns:")
  SU.debug("ftml", SILE.scratch.ftml.tablecolumns)
  SU.debug("ftml", "table column list end")

  -- Process some header text
  SILE.call("skip", {height="2pt plus 0pt minus 0pt"})
  if head_title then SILE.call("ftml:title", {}, head_title) end
  if head_comment then SILE.call("ftml:comment", {}, head_comment) end

end)

SILE.registerCommand("testgroup", function (options, content)
  SU.debug("ftml", "entering testgroup")
  SILE.scratch.ftml.testgroup = {}
  -- get label and background attributes from testgroup element; get comment subelement
  local testgroup_label = options["label"]
  local testgroup_background = options["background"] -- store for possible use at test level
  local testgroup_comment = SILE.findInTree(content, "comment")
  if type(testgroup_comment) == "table" then testgroup_comment = testgroup_comment[1] end
  if type(testgroup_comment) == "nil" or testgroup_comment == "" then testgroup_comment = " " end
  SU.debug("ftml", testgroup_label .. " " .. testgroup_background .. " " .. testgroup_comment)
  -- Need to output testgroup_label and testgroup_comment
  SILE.typesetter:leaveHmode()
  SILE.call("ftml:testgrouplabel", {}, {testgroup_label})
  if testgroup_comment then
SU.debug("ftml", testgroup_comment)
    SILE.call("ftml:testgroupcomment", {}, {testgroup_comment})
  end
  SILE.process(content)
  SILE.call("skip", {height="2pt plus 0pt minus 0pt"})
  SU.debug("ftml", "exiting testgroup")
end)

SILE.registerCommand("test", function (options, content)
  SU.debug("ftml", "entering test")
  local row = #(SILE.scratch.ftml.testgroup)+1 -- add a row for each test element
  SILE.scratch.ftml.testgroup[row] = {}
--  SILE.scratch.ftml.line = {}
  local test_label = options["label"]
  local test_background = options["background"] -- or testgroup_background
  local test_rtl = options["rtl"]
  local test_stylename = options["stylename"]
  SU.debug('ftml', 'test_label=' .. test_label)
  SU.debug('ftml', 'test_background=' .. test_background)
  SU.debug('ftml', 'test_rtl=' .. test_rtl)
  SU.debug('ftml', 'test_stylename=' .. test_stylename)
  local test_comment_element = SILE.findInTree(content, "comment")
--  if test_comment_element then test_comment = test_comment_element[1] else test_comment = nil end
  SU.debug('ftml','test_comment=' .. test_comment)
  SILE.scratch.ftml.testgroup[row].label =      test_label      or ""
  SILE.scratch.ftml.testgroup[row].background = test_background or ""
--  SILE.scratch.ftml.testgroup[row].rtl =        test_rtl        or ""
  if test_rtl == "True" then
    SILE.scratch.ftml.testgroup[row].rtl = "RTL"
  else
    SILE.scratch.ftml.testgroup[row].rtl = "LTR"
  end
  SU.debug('ftml', '.rtl=' .. SILE.scratch.ftml.testgroup[row].rtl)
  SILE.scratch.ftml.testgroup[row].stylename =  test_stylename  or ""
  SILE.scratch.ftml.testgroup[row].comment =    test_comment    or ""
  SILE.process(content)
--  SU.debug('ftml', 'string=' .. SILE.scratch.ftml.testgroup[row].string)
--  SILE.repl()
--  SILE.call("col-label")
  SU.debug("ftml", "exiting test")
end)

local function expandslashu(s) -- given string s, expand any \uxxxx, \uxxxxx, \uxxxxxx characters and return new string
  local t = {}
  local i = 0
  local j = 0
  while true do
    i, j = string.find(s,"\\u%x%x%x%x%x?%x?",i+1)
    if i == nil then break end
    table.insert(t, {i,j})
  end
  if #t then -- if #t non-zero, then at least one \uxxxx sequence found
    news = ""
    startspan = 1
    for _, x in ipairs(t) do
      i = x[1]
      j = x[2]
      endspan = i-1
      news = news .. string.sub(s,startspan,endspan) .. SU.utf8char(tonumber("0x" .. string.sub(s,i+2,j)))
      startspan = j+1
    end
    news = news .. string.sub(s,startspan,-1)
    s = news
  end
  return s
end

SILE.registerCommand("string", function (options, content)
  SU.debug("ftml", "entering string")
  local any_em_elements = (SILE.findInTree(content, 'em') ~= nil)
  SU.debug("ftml", "<em> elements found: " .. tostring(any_em_elements))
  SU.debug("ftml", "content: " .. content)
  SILE.scratch.ftml.stylename = SILE.scratch.ftml.testgroup[#(SILE.scratch.ftml.testgroup)].stylename
  SILE.scratch.ftml.background = SILE.scratch.ftml.testgroup[#(SILE.scratch.ftml.testgroup)].background
  SU.debug("ftml", "stylename: " .. SILE.scratch.ftml.stylename)
  --SILE.repl()
  if SILE.scratch.ftml.stylename and SILE.scratch.ftml.stylename ~= "" then
    SU.debug("ftml", SILE.scratch.ftml.head.styles[SILE.scratch.ftml.stylename].lang)
    SU.debug("ftml", SILE.scratch.ftml.head.styles[SILE.scratch.ftml.stylename].feats)
  end
  SILE.call("skip", {height="2pt plus 0pt minus 0pt"})
--[[
  if #SILE.scratch.ftml.background > 0 then
    SILE.call("color", {color = SILE.scratch.ftml.background}, function ()
      SILE.call("rebox", {width=0,height=0}, function ()
       for c = 1,#colinfo do
          if colinfo[c].name == "gutter" then
            SILE.call("glue", {width=colinfo[c].width.."pt", height=12})
          else
            SILE.call("hrule", {width=colinfo[c].width, height=12})
          end
        end
      end)
    end)
  end
--]]
  for c = 1,#colinfo do
    SU.debug("ftml", "Looping string " .. c)
    SILE.call("rebox", {width = colinfo[c].width }, function ()
      -- reset all columns to defaults
      SILE.settings.set("font.family", "Gentium Plus")
      SILE.settings.set("font.filename", "")
      SILE.settings.set("font.weight", 400)
      SILE.settings.set("font.style", "normal")
      SILE.settings.set("font.size", 8)
      SILE.settings.set("font.direction", "LTR")
      SILE.settings.set("font.features", "")
      SILE.settings.set("document.language", "en")
      SILE.settings.set("document.parindent", SILE.nodefactory.glue())
      local colname = colinfo[c].name -- label, stringX, stylename, comment
      SU.debug("ftml", "colname: "..colname .. " width: " ..colinfo[c].width)
      if not string.find(colname, "string") then -- if colname doesn't contain "string"
        SILE.settings.set("linespacing.method", "fixed")
        SILE.settings.set("linespacing.fixed.baselinedistance", SILE.length({length=8, stretch=0, shrink=0}))
        local outputtext = SILE.scratch.ftml.testgroup[#(SILE.scratch.ftml.testgroup)][colname]
        if not outputtext then outputtext = SU.utf8char(160) end -- U+00A0 to hold place, otherwise Vglue disappears and spacing is off
        -- or try using SILE.typesetter:pushExplicitVglue
        SILE.typesetter:typeset(outputtext)
        -- SILE.typesetter:typeset(SILE.scratch.ftml.testgroup[#(SILE.scratch.ftml.testgroup)][colname])
      else -- string
        local fontnumstring,_ = string.gsub(colname,"string","")
        local fontnum = tonumber(fontnumstring)
        if SILE.scratch.ftml.fontlist[fontnum].filename then
          SILE.settings.set("font.filename", SILE.scratch.ftml.fontlist[fontnum].filename)
        elseif SILE.scratch.ftml.fontlist[fontnum].family then
          SILE.settings.set("font.family", SILE.scratch.ftml.fontlist[fontnum].family)
          if SILE.scratch.ftml.fontlist[fontnum].bold then
            SILE.settings.set("font.weight", 700)
          else
            SILE.settings.set("font.weight", 400)
          end
          if SILE.scratch.ftml.fontlist[fontnum].italic then
            SILE.settings.set("font.style", "italic")
          else
            SILE.settings.set("font.style", "normal")
          end
        end
        SILE.settings.set("font.size", SILE.scratch.ftml.fontsize)
        SILE.settings.set("linespacing.method", "fixed")
--        SILE.settings.set("linespacing.fixed.baselinedistance", SILE.length({length=1.5*SILE.scratch.ftml.fontsize, stretch=0, shrink=0}))
--        SILE.settings.set("linespacing.fixed.baselinedistance", SILE.length({length=8, stretch=0, shrink=0}))
        SILE.settings.set("linespacing.fixed.baselinedistance", SILE.length({length=0.5*SILE.scratch.ftml.fontsize, stretch=0, shrink=0}))
        -- isrtl = SILE.scratch.ftml.testgroup[#(SILE.scratch.ftml.testgroup)].rtl
        -- SILE.settings.set("font.direction", isrtl)
        -- SILE.typesetter.frame.direction = isrtl
        SU.debug("ftml", SILE.scratch.ftml.stylename)
        SU.debug("ftml", SILE.settings.get("font.direction"))
        if SILE.scratch.ftml.stylename and SILE.scratch.ftml.stylename ~= "" then
          SILE.settings.set("font.features", SILE.scratch.ftml.head.styles[SILE.scratch.ftml.stylename].feats)
          SILE.settings.set("document.language", SILE.scratch.ftml.head.styles[SILE.scratch.ftml.stylename].lang)
          SU.debug("ftml", SILE.scratch.ftml.head.styles[SILE.scratch.ftml.stylename].feats)
          SU.debug("ftml", SILE.settings.get("font.features"))
          SU.debug("ftml", SILE.scratch.ftml.head.styles[SILE.scratch.ftml.stylename].lang)
        end
        -- NOT supported: background color from SILE.scratch.ftml.testgroup[#(SILE.scratch.ftml.testgroup)].background
        if any_em_elements then
          for _, x in ipairs(content) do
            if type(x) == 'string' then
              -- output x in grey (with \u conv)
              SILE.call("color", {color='grey'}, {expandslashu(x)})
            elseif type(x) == 'table' and x.tag == 'em' then
              -- output x[1] normally (with \u conv)
              SILE.typesetter:typeset(expandslashu(x[1]))
            else
              -- ignore unknown stuff (or raise error)
            end
          end
        else -- output content[1] normally (with \u conversion)
          SILE.typesetter:typeset(expandslashu(content[1]))
        end
      end
      SU.debug("ftml", "just printed " .. colname .. " column: " .. c)
    end)
  end
  SILE.typesetter:leaveHmode()
  for c = 1,#colinfo do
    if colinfo[c].name == "gutter" then
      SILE.call("glue", {width=colinfo[c].width.."pt", height=0.5})
    else
      SILE.call("hrule", {width=colinfo[c].width, height=0.5})
    end
  end
  SILE.typesetter:leaveHmode()
  SILE.typesetter:pushExplicitVglue({height=SILE.length({ height = 20, stretch = 0, shrink = 0}) })
  SILE.typesetter:typeset(SU.utf8char(160))
  SILE.typesetter:leaveHmode()
  SU.debug("ftml", "exiting string")
end)

return ftml
