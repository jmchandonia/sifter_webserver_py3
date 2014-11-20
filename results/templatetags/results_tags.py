from django import template
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import matplotlib.cm as cmx

my_map =plt.get_cmap('YlOrBr')
cNorm  = colors.Normalize(vmin=0, vmax=150)
scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=my_map)

my_map2 =plt.get_cmap('Greys')
cNorm2  = colors.Normalize(vmin=-50, vmax=101)
scalarMap2 = cmx.ScalarMappable(norm=cNorm2, cmap=my_map2)




register = template.Library()
@register.filter
def hash(h, key):
    return h[key]


@register.filter
def get_color_rgba(score):
    c=scalarMap.to_rgba(round(float(score)*100))
    return '(%d,%d,%d,%s)'%(round(c[0]*255),round(c[1]*255),round(c[2]*255),c[3]*.5)

@register.filter
def get_color_rgb2(score):
    c=scalarMap2.to_rgba(round(float(score)*100))
    return '(%d,%d,%d,%s)'%(round(c[0]*255),round(c[1]*255),round(c[2]*255),c[3]*1)

