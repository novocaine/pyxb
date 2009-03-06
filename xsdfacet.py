import PyWXSB.XMLSchema as xs
import PyWXSB.Namespace as Namespace
#from PyWXSB.generate import PythonGenerator as Generator

import types
import sys
import traceback
from xml.dom import minidom
from xml.dom import Node

Namespace.XMLSchema.modulePath(None)
TargetNamespace = None

def PrefixedName (value):
    if value.__module__ == xs.datatypes.__name__:
        return value.__name__
    if value.__module__ == xs.facets.__name__:
        return 'facets.%s' % (value.__name__,)
    assert False

def facetLiteral (value):
    if isinstance(value, xs.facets._Enumeration_mixin):
        return '%s.%s' % (facetLiteral(value.__class__), value._CF_enumeration.tagForValue(value))
    if isinstance(value, xs.datatypes._PST_mixin):
        return value.pythonLiteral()
    if isinstance(value, type) and issubclass(value, xs.datatypes._PST_mixin):
        return PrefixedName(value)
    if isinstance(value, xs.facets.Facet):
        #return '%s.XsdSuperType()._CF_%s' % (value.ownerTypeDefinition().ncName(), value.Name())
        return '%s._CF_%s' % (value.ownerTypeDefinition().ncName(), value.Name())
    if isinstance(value, types.StringType):
        return "'%s'" % (value,)
    if isinstance(value, types.UnicodeType):
        return "u'%s'" % (value,)
    if isinstance(value, xs.facets._PatternElement):
        return facetLiteral(value.pattern)
    if isinstance(value, xs.facets._EnumerationElement):
        return facetLiteral(value.value)
    if isinstance(value, xs.structures.SimpleTypeDefinition):
        return value.ncName()
    print 'Unexpected literal type %s' % (type(value),)
    return str(value)

files = sys.argv[1:]
if 0 == len(files):
    files = [ 'schemas/XMLSchema.xsd' ]

try:
    wxs = xs.schema().CreateFromDOM(minidom.parse(files[0]))
    ns = wxs.getTargetNamespace()
    TargetNamespace = ns

    type_defs = ns.typeDefinitions()
    emit_order = []
    while 0 < len(type_defs):
        new_type_defs = []
        for td in type_defs:
            if not isinstance(td, xs.structures.SimpleTypeDefinition):
                continue
            if td.targetNamespace() != ns:
                continue
            if (Namespace.XMLSchema == td.targetNamespace()) and (not td.isBuiltin()):
                continue
            dep_types = td.dependentTypeDefinitions()
            ready = True
            for dtd in dep_types:
                if dtd.targetNamespace() != ns:
                    continue
                if dtd == td:
                    continue
                if not (dtd in emit_order):
                    ready = False
                    break
            if ready:
                emit_order.append(td)
            else:
                new_type_defs.append(td)
        type_defs = new_type_defs

    outf = file('datatypesi.tmp', 'w')
    outf.write('''
import facets
from datatypes import *
''')

    for td in emit_order:
        #print 'Emitting %d facets in %s' % (len(td.facets()), td)
        for (fc, fi) in td.facets().items():
            if (fi is None) and (fc in td.baseTypeDefinition().facets()):
                # Nothing new here
                #print 'No instance'
                continue
            if (fi is not None) and (fi.ownerTypeDefinition() != td):
                # Did this one in an ancestor
                #print 'Parent instance'
                continue
            argset = { }
            is_collection = issubclass(fc, xs.facets._CollectionFacet_mixin)
            if issubclass(fc, xs.facets._LateDatatype_mixin):
                argset['value_datatype'] = fc.BindingValueDatatype(td)
            if fi is not None:
                if not is_collection:
                    argset['value'] = fi.value()
                if fi.superFacet() is not None:
                    argset['super_facet'] = fi.superFacet()
            facet_var = '%s._CF_%s' % (td.ncName(), fc.Name())
            outf.write("%s = facets.CF_%s(%s)\n" % (facet_var, fc.Name(), ', '.join([ '%s=%s' % (key, facetLiteral(val)) for (key, val) in argset.items() ])))
            if (fi is not None) and is_collection:
                for i in fi.items():
                    argset = { }
                    if isinstance(i, xs.facets._EnumerationElement):
                        outf.write("%s.%s%s = %s._CF_enumeration.addKeyword(tag=%s)\n" % (td.ncName(), 'EV_', i.value, td.ncName(), facetLiteral(i.value)))

except Exception, e:
    sys.stderr.write("%s processing %s:\n" % (e.__class__, file))
    traceback.print_exception(*sys.exc_info())


