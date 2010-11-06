#!/usr/bin/python

from waflib import Context, Utils
import os, shutil

def configure_tests(ctx, fonts) :
    res = set(['xetex', 'grsvg', 'firefox', 'xdvipdfmx', 'xsltproc', 'firefox'])
    return res

def make_tex(task, mf, font) :
    texdat = r'''
\font\test="[%s]%s" at 12pt
\hoffset=-.2in \voffset=-.2in \nopagenumbers \vsize=10in
\obeylines
\test
\input %s
\bye
''' % (font, mf, task.inputs[0].bldpath())
    task.outputs[0].write(texdat)
    return 0
    
def copy_task(task) :
    shutil.copy(task.inputs[0].bldpath(), task.outputs[0].bldpath())
    return 0

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
        if getattr(fontmap[f], 'graphite', None) :
            modes['gr'] = "/GR"
        if getattr(fontmap[f], 'sfd_master', None) or getattr(fontmap[f], 'opentype', None) :
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
                    ctx(rule = lambda t: make_tex(t, mf, fontmap[f].target),
                        source = n, target = targ)
                    textfiles.append((targ, n))

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
            for n in texfiles :
                targfile = n.get_bld().bld_base() + os.path.splitext(f)[0] + ".tex"
                targ = ctx.path.find_or_declare(targfile)
                ctx(rule = copy_task, source = n, target = targ)
                textfiles.append((targ, n))
            for n in textfiles :
                targ = n[0].get_bld()
                print str(n) + " depends on " + str(ctx.bldnode.find_resource(fontmap[f].target).abspath())
                ctx(rule = '${XETEX} --no-pdf --output-directory=' + targ.bld_dir() + ' ${SRC}',
                    source = n[0], target = targ.change_ext('.xdv'),
                    scan = lambda t: ((ctx.bldnode.find_resource(fontmap[f].target),), ()))
                if target == 'pdfs' :
                    ctx(rule = '${XDVIPDFMX} -o ${TGT} ${SRC}', source = targ.change_ext('.xdv'), target = targ.change_ext('.pdf'))


