#!/usr/bin/python

from subprocess import Popen, PIPE
import os
import package

class Keyboard(object) :
   
    def __init__(self, *k, **kw) :
        if not 'target' in kw : kw['target'] = kw['source'].replace('.kmn', '.kmx')
        if not 'svg' in kw : kw['svg'] = kw['source'].replace('.kmn', '.svg')
        if not 'xml' in kw : kw['xml'] = kw['source'].replace('.kmn', '.xml')
        if not 'pdf' in kw : kw['pdf'] = kw['source'].replace('.kmn', '.pdf')
#        if not 'fontname' in kw : kw['fontname'] = Popen(r"ttfeval -e 'print scalar $f->{q/name/}->read->find_name(2)' " + kw['font'], shell = True, stdout=PIPE).communicate()[0]
        if not 'fontsize' in kw : kw['fontsize'] = 18
        if not 'fontdir' in kw : kw['fontdir'] = 'kbdfonts'
        if not 'kbdfont' in kw : kw['kbdfont'] = os.path.join(kw['fontdir'], os.path.split(kw['font'])[1])
        for k, v in kw.items() : setattr(self, k, v)
        if not hasattr(self, 'package') :
            self.package = package.global_package()
        self.package.add_kbd(self)
 
    def get_build_tools(self, ctx) :
        res = set(['kmn2xml', 'kmnxml2svg', 'inkscape', 'ttfeval', 'cp'])
        try: ctx.find_program('kmcomp', var = 'KMCOMP')
        except:
            path = os.path.join(os.getenv('HOME'), '.wine', 'drive_c', 'Program Files', 'Tavultesoft', 'Keyman Developer', 'kmcomp.exe')
            if os.path.exists(path) : ctx.env['KMCOMP'] = 'wine "' + path + '"'
        fdir = ctx.bldnode.make_node(self.fontdir)
        fdir.mkdir()
        fconf = fdir.make_node('fonts.conf')
        if not os.path.exists(fconf.bldpath()) :
            dat = '''<fontconfig>

    <include ignore_missing="yes">/etc/fonts/fonts.conf</include>
    <dir>%s</dir>
    <cachedir>%s</cachedir>

</fontconfig>
''' % (fdir.abspath(), fdir.abspath())
            fconf.write(dat)

        return res

    def build(self, bld) :
        if bld.env['KMCOMP'] :
            bld(rule = '${KMCOMP} ${SRC} ${TGT}', source = self.source, target = self.target)

    def build_pdf(self, bld) :
        self.build_svg(bld)
        bld(rule = 'FONTCONFIG=' + self.fontdir + " ${INKSCAPE} -f ${SRC[0].bldpath()} -A ${TGT} -T -d 2400", shell = 1, source = [self.svg, self.kbdfont], target = self.pdf)

    def build_svg(self, bld) :
        bld(rule = '${KMN2XML} ${SRC} > ${TGT}', shell = 1, source = self.source, target = self.xml)
        bld(rule = '${CP} ${SRC} ${TGT}', source = self.font, target = self.kbdfont)
        bld(rule = '${KMNXML2SVG} -s ' + str(self.fontsize) + ' -f "' + self.fontname + '" ${SRC} ${TGT}', source = self.xml, target = self.svg)
    
def onload(ctx) :
    varmap = { 'kbd' : Keyboard }
    for k, v in varmap.items() :
        if hasattr(ctx, 'wscript_vars') :
            ctx.wscript_vars[k] = v
        else :
            setattr(ctx.g_module, k, v)

