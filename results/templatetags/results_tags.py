from django import template
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import matplotlib.cm as cmx

my_map =plt.get_cmap('Blues')
cNorm  = colors.Normalize(vmin=0, vmax=101)
scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=my_map)

register = template.Library()
@register.filter
def hash(h, key):
    return h[key]


@register.filter
def get_color_rgba(score):
    c=scalarMap.to_rgba(round(float(score)*100))
    return '(%d,%d,%d,%s)'%(round(c[0]*255),round(c[1]*255),round(c[2]*255),c[3]*.5)

