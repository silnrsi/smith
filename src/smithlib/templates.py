''' templates '''
__url__ = 'http://github.com/silnrsi/smith'
__copyright__ = 'Copyright (c) 2011-2025 SIL Global (http://www.sil.org)'
__author__ = 'Martin Hosken'
__license__ = 'Released under the 3-Clause BSD License (http://opensource.org/licenses/BSD-3-Clause)'



FontTests = {
    'index_head' : """
    <!DOCTYPE html>
    <html><head>
    <meta charset="utf-8">
    <meta name="Description" lang="en" content="Index for generated tests (smith automated font testing)">
    <meta name="author" content="smith">

    <style>
    body {
       background-color: linen;
       font-size: 12px;
       padding: 25;
       margin: 25;
       margin-left: 25px;
       margin-right: 25px;
       font-family: 'Fira Sans', 'Noto Sans', 'Source Sans',  sans-serif;
    }
    h1 {
       color: black;
    }
    h2 {
       color: black;
    }
    p {
       color: black;
       text-align: left;
       font-size: 13px;
    }
    table, th, td {
       border-collapse: collapse;
       border-spacing: 7px;
       padding: 7px;
       text-align: left;
       border: 1px solid black;
       border-bottom: 1px solid #ddd;
    }
    th {
       height: 20px;
       font-size: 14px;
       background-color: lightgrey;
    }
    td:hover {
       background-color: #f5f5f5;
    }

    </style>
    </head>
    <body>
    <h1> Index for generated tests (smith automated font testing)</h1>
    <br>
    <br>

    """,
    'index_tail' : '</body></html>\n'
}

TestCommand = {
    'init_head' : "<h2>{}</h2>\n<table><tr>\n<th>{}</th>",
    'init_tail' : "</table> <br> \n",
    'head_row' : "  <th>{}</th>",
    'head_row_end' : "</tr>\n",
    'row_head' : "  <tr><th>{}</th>",
    'row_tail' : "</tr>\n",
    'cell_head' : "<td>",
    'cell_filename' : '{} ',
    'cell_content' : '<a href="{}" target="_blank">open results</a>',
    'cell_tail' : "</td>"
}

FtmlTestCommand = {
    'head' : r'''<?xml version="1.0"?>
<ftml version="1.0">
  <head>
    <columns comment="30%" label="25%" string="45%"/>
    <fontsrc/>
    <styles/>
  </head>
  <testgroup label="main">
''',
    'content' : '    <test label="{}">\n      <string>{}</string>\n    </test>\n',
    'tail' : r'''</testgroup>
</ftml>
'''
}

TexTestCommand = {
    'txt' : r'''\font\test="[./{0}]{1}" at {7}pt
\hoffset=-.2in \voffset=-.2in \nopagenumbers \vsize=10in
\catcode"200B=\active \def^^^^200b{{\hskip0pt\relax}}
\emergencystretch=3in \rightskip=0pt plus 1in \tolerance=10000 \count0=0

Test for {2}

{4}

Input file: {5}

(XeTeX \XeTeXrevision \space with {3} \ifcase\XeTeXfonttype\test\TeX\or AAT\or OpenType\or Graphite\fi \space support - smith automated font testing)

-------------------------------------------------



\def\plainoutput{{\shipout\vbox{{\makeheadline\pagebody\makefootline}}\ifnum\outputpenalty>-2000 \else\dosupereject\fi}}
\XeTeXuseglyphmetrics=0
%\XeTeXlinebreaklocale "G"
\obeylines
\everypar{{\global\advance\count0by1\llap{{\tt\the\count0\quad}}}}
\test
\input ./{6}
\bye
''',
        'htex' : r'''\def\buildfont{{"[./{0}]{1}"}}
\input {2}
\bye
'''
}

Waterfall = {
    'head' : r'''\hoffset=-.2in \voffset=-.2in \nopagenumbers \vsize=10in
\catcode"200B=\active \def^^^^200b{{\hskip0pt\relax}}
\emergencystretch=3in \rightskip=0pt plus 1in \tolerance=10000 \count0=0
\def\plainoutput{{\shipout\vbox{{\makeheadline\pagebody\makefootline}}\ifnum\outputpenalty>-2000 \else\dosupereject\fi}}

Waterfall for {0} - {1} {2} - {3} - XeTeX \XeTeXrevision

--------------------------------------------------



''',
    'content' : r'''\font\test="[./{0}]{1}{2}" at {3} pt \baselineskip={4} pt
\noindent\test {5}
\par
''',
    'tail' : r'''\bye
'''
}

CrossFont = {
    'head' : r'''\hoffset=-.2in \voffset=-.2in \nopagenumbers \vsize=10in
\catcode"200B=\active \def^^^^200b{{\hskip0pt\relax}}
\emergencystretch=3in \rightskip=0pt plus 1in \tolerance=10000 \count0=0
\def\plainoutput{{\shipout\vbox{{\makeheadline\pagebody\makefootline}}\ifnum\outputpenalty>-2000 \else\dosupereject\fi}}

Crossfont specimen - {0} {1} - {2} - XeTeX \XeTeXrevision

--------------------------------------------------


''',
    'content' : r'''\font\test="[./{0}]{1}{2}" at {3} pt
\noindent\hbox to 2in {{\vbox{{\hsize=2in\noindent \rm {4}}}}}
\test {5}
\par
''',
    'tail' : r'''\bye
'''
}

