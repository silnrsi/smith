
FontTests = {
    'index_head' : u"<html><head></head><body>\n",
    'index_tail' : u'</body></html>\n'
}

TestCommand = {
    'init_head' : u"<h2>{}</h2>\n<table><tr>\n<th>{}</th>",
    'init_tail' : u"</table>\n",
    'head_row' : u"  <th>{}</th>",
    'head_row_end' : u"</tr>\n",
    'row_head' : u"  <tr><th>{}</th>",
    'row_tail' : u"</tr>\n",
    'cell_head' : u"<td>",
    'cell_content' : u'<a href="{}">Results</a>',
    'cell_tail' : u"</td>"
}

FtmlTestCommand = {
    'head' : ur'''<?xml version="1.0"?>
<ftml version="1.0">
  <head>
    <columns comment="30%" label="25%" string="45%"/>
    <fontsrc/>
    <styles/>
  </head>
  <testgroup label="main">
''',
    'content' : u'    <test label="{}">\n      <string>{}</string>\n    </test>\n',
    'tail' : ur'''</testgroup>
</ftml>
'''
}

TexTestCommand = {
    'txt' : ur'''\font\test="[./{0}]{1}" at 12pt
\hoffset=-.2in \voffset=-.2in \nopagenumbers \vsize=10in
\catcode"200B=\active \def^^^^200b{{\hskip0pt\relax}}
\emergencystretch=3in \rightskip=0pt plus 1in \tolerance=10000 \count0=0

Test for {2} - {3} using
\ifcase\XeTeXfonttype\test\TeX\or OpenType\or Graphite\fi
\space- {4} - XeTeX \XeTeXrevision

Input file: {5}

--------------------------------------------------



\def\plainoutput{{\shipout\vbox{{\makeheadline\pagebody\makefootline}}\ifnum\outputpenalty>-2000 \else\dosupereject\fi}}
\obeylines
\everypar{{\global\advance\count0by1\llap{{\tt\the\count0\quad}}}}
\test
\input ./{6}
\bye
''',
        'htex' : ur'''\def\buildfont{{"[./{0}]{1}"}}
\input {2}
\bye
'''
}

Waterfall = {
    'head' : ur'''\hoffset=-.2in \voffset=-.2in \nopagenumbers \vsize=10in
\catcode"200B=\active \def^^^^200b{{\hskip0pt\relax}}
\emergencystretch=3in \rightskip=0pt plus 1in \tolerance=10000 \count0=0
\def\plainoutput{{\shipout\vbox{{\makeheadline\pagebody\makefootline}}\ifnum\outputpenalty>-2000 \else\dosupereject\fi}}

Waterfall for {0} - {1} {2} - {3} - XeTeX \XeTeXrevision

--------------------------------------------------



''',
    'content' : ur'''\font\test="[./{0}]{1}{2}" at {3} pt \baselineskip={4} pt
\noindent\test {5}
\par
''',
    'tail' : ur'''\bye
'''
}

CrossFont = {
    'head' : ur'''\hoffset=-.2in \voffset=-.2in \nopagenumbers \vsize=10in
\catcode"200B=\active \def^^^^200b{{\hskip0pt\relax}}
\emergencystretch=3in \rightskip=0pt plus 1in \tolerance=10000 \count0=0
\def\plainoutput{{\shipout\vbox{{\makeheadline\pagebody\makefootline}}\ifnum\outputpenalty>-2000 \else\dosupereject\fi}}

Crossfont specimen - {0} {1} - {2} - XeTeX \XeTeXrevision

--------------------------------------------------


''',
    'content' : ur'''\font\test="[./{0}]{1}{2}" at {3} pt
\noindent\hbox to 2in {{\vbox{{\hsize=2in\noindent \rm {4}}}}}
\test {5}
\par
''',
    'tail' : ur'''\bye
'''
}

