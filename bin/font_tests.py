#!/usr/bin/python

from waflib import Context, Utils
import os

def configure_tests(ctx, fonts) :
    res = set(['xetex', 'grsvg', 'firefox', 'xdvipdfmx', 'xsltproc', 'firefox'])
    return res

def build_tests(ctx, fonts, target) :

    testsdir = ctx.env['TESTDIR']
    if not testsdir : testsdir = "tests"
    testsdir += os.sep

    fontmap = dict([[getattr(f, 'test_suffix', f.id), f] for f in fonts])
    
    # make list of source tests to run against fonts, build if necessary
    txtfiles = ctx.path.ant_glob(testsdir + "*.txt")
    texfiles = ctx.path.ant_glob(testsdir + "*.tex")
    htxtfiles = ctx.path.ant_glob(testsdir + "*.htxt")
    htxttfiles = []
    textfiles = []

    for n in htxtfiles :
        targ = n.get_bld().change_ext('.txt')
        ctx(rule=r"perl -CSD -pe 's{\\[uU]([0-9A-Fa-f]+)}{pack(qq/U/, hex($1))}oge' ${SRC} > ${TGT}", shell = 1, source = n, target = targ)
        htxttfiles.append(targ)

#    import pdb; pdb.set_trace()
    for f in fontmap :
        modes = {}
        if getattr(fontmap[f], 'gdl_source', None) :
            modes['gr'] = "/GR"
        if getattr(fontmap[f], 'sfd_master', None) or getattr(fontmap[f], 'volt_source', None) :
            t = "/ICU"
            if getattr(fontmap[f], 'script', None) :
                t += ":script=" + fontmap[f].script
            modes['ot'] = t
        for n in txtfiles + htxttfiles :
            for m, mf in modes.items() :
                nfile = os.path.split(n.bld_base())[1]
                lang = nfile.partition('_')[0]
                if lang == nfile : lang == None
                else :
                    mf += ":language=" + lang

                if target == "pdfs" or target == 'test' :
                    targfile = n.get_bld().bld_base() + os.path.splitext(f)[0] + "_" + m + ".tex"
                    targ = ctx.path.find_or_declare(targfile)
                    textfiles.append(targ)
                    texdat = r'''
\font\test="[%s]%s" at 12pt
\hoffset=-.2in \voffset=-.2in \nopagenumbers \vsize=10in
\obeylines
\test
\input %s
\bye
''' % (fontmap[f].target, mf, n.bldpath())
                    targ.write(texdat)
                    targ.sig=Utils.h_file(targ.abspath())

                elif target == 'svg' :
                    if m == 'gr' :
                        rend = 'graphite'
                    else :
                        rend = 'icu'
                    if lang :
                        rend += " --feat lang=" + lang
                    targfile = n.get_bld().bld_base() + os.path.splitext(f)[0] + "_" + m + '.svg'
                    ctx(rule='${GRSVG} ' + fontmap[f].target + ' -i ${SRC} -o ${TGT} --renderer ' + rend, source = n, target = targfile)

        if target == 'pdfs' or target == 'test' :
            for n in texfiles + textfiles :
                targ = n.get_bld()
                ctx(rule = '${XETEX} --no-pdf --output-directory=' + targ.bld_dir() + ' ${SRC}', source = n, target = targ.change_ext('.xdv'))
                if target == 'pdfs' :
                    ctx(rule = '${XDVIPDFMX} -o ${TGT} ${SRC}', source = targ.change_ext('.xdv'), target = targ.change_ext('.pdf'))


