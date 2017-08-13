
# TO DO: Set max limit for smoothness slider, f(number of points, variance of data)
# TO DO: choice over controlling number of knots or smoothness
from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.plotting import Figure
from bokeh.models import Circle, ColumnDataSource, Span
from bokeh.models.callbacks import CustomJS
from bokeh import events
from bokeh.models.widgets import Select, TextInput, Slider, Div

import numpy as np
import math
from scipy.interpolate import splev, splrep

CIRCLE_RADIUS = 7

def sim_sort_lists(list1, list2):
    ''' sort the second list based on the first one'''
    r = zip(*sorted(zip(list1,list2)))
    return list(r[0]), list(r[1])

def distance(p1, p2):
    return ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5

p = Figure(plot_width=500, plot_height=300, y_range=(-2,2), x_range=(0,2*math.pi), min_border_top=10, min_border_left=40  )
p.toolbar.active_drag = None

# A 'curvy' function that we can use to see how good the splines approximate it
x=np.linspace(0, 2*math.pi, num=100)
source_function = ColumnDataSource(data=dict(x=x, y=np.sin(x)))
p.line(x='x', y='y', source=source_function, color="blue", line_width=1)

# A few datapoints to get us started
source_datapoints = ColumnDataSource(data=dict(x=[0, 0.5*math.pi, 1*math.pi, 1.5*math.pi, 2*math.pi], y=[0, np.sin(0.5*math.pi), np.sin(1*math.pi), np.sin(1.5*math.pi), np.sin(2*math.pi)]))
p.circle(x='x', y='y', size=CIRCLE_RADIUS, source=source_datapoints, color="blue", line_width=3)

source_spline = ColumnDataSource(data=dict(x=[], y=[]))

# The knots locations
source_knots = ColumnDataSource(data=dict(x=[]))
p.ray(x='x', y=-10, source=source_knots, color="green", line_dash='dashed', line_width=1, length=0, angle=90, angle_units="deg",)

slider_smooth = Slider(start=0, end=10, step=0.2, value=0, title="smoothness", callback_policy='mouseup')
# slider_knots = Slider(start=1, end=20, step=1, value=3, title="knots")
select_degree = Select(title="Curve order:", value="3", options=[("1","Linear (1 degree)"), ("2","Quadratic (2 degrees)"), ("3","Cubic (3 degrees)"), ("4","Quartic (4 degrees)"), ("5","Quintic (5 degrees)")])

# Show a warning when (number of datapoints) < (order of curve + 1)
div = Div(text="<font color=black>This spline requires at least 4 points</font>", width=400, height=100)
def update_div(attr, old, new):
    min_points = int(select_degree.value)+1
    color="black"
    extra = ""
    if min_points>len(source_datapoints.data['x']):
        color="red"
        extra = ", please add "+ str(min_points-len(source_datapoints.data['x'])) +" more!"
    div.text="<font color="+color+">This spline requires at least "+str(min_points)+" points" +extra+"</font>"


def update_source_spline(attr, old, new):
    sorted_x, sorted_y = sim_sort_lists(source_datapoints.data['x'], source_datapoints.data['y'])
    # x_knots=list( np.linspace(0,2*math.pi, num=slider_knots.value+2) )[1:-1]
    # print x_knots
    tck=splrep(sorted_x, sorted_y, k=int(select_degree.value), s=float(slider_smooth.value) ) # t=x_knots,
    source_spline.data = dict(x=x, y=splev(x,tck))
    p.line('x', 'y', color="red", source=source_spline)
    source_knots.data = dict(x=tck[0])
    # cs = CubicSpline(sorted_x, sorted_y, axis=0, bc_type='natural', extrapolate=None)
    # source_spline = ColumnDataSource(data=dict(x=x, y=cs(x)))



# This way the slider triggers only when hte mouse is released
# Otherwise at higher curve orders with many points it could get slow
# source_dummy is just used to trigger the callback to update_source_spline
source_dummy = ColumnDataSource(data=dict(value=[]))
source_dummy.on_change('data', update_source_spline)
# slider_smooth.on_change('value', update_source_spline)
slider_smooth.callback = CustomJS(args=dict(source_dummy=source_dummy), code="""
    source_dummy.data = { value: [cb_obj.value] }
""")


def display_event():

    return CustomJS(args=dict(p=p,  source_datapoints_JS=source_datapoints),  code="""

    function distance(p1, p2) {
        return Math.sqrt( Math.pow(p1[0]-p2[0] , 2) + Math.pow(p1[1]-p2[1], 2) );
    }

    var x_scale = p.inner_width / (p.x_range.end - p.x_range.start)
    var y_scale = p.inner_height / (p.y_range.end - p.y_range.start)
    var CIRCLE_RADIUS = %s;
    var data = source_datapoints_JS.data
    var px_JS=new Array();
    var py_JS=new Array();

    // TO DO: do this only when data is changed (maybe a source_update_flag)
    for (i=0; i<data['x'].length; i++){
        px_JS.push( (data['x'][i]-p.x_range.start) * x_scale + p.min_border_left);
        py_JS.push( (p.y_range.end - data['y'][i]) * y_scale + p.min_border_top);
    }

    if (cb_obj.event_name == 'tap') {
        var delete_point=-1
        for (i=0; i<data['x'].length; i++){
            if (distance( [cb_obj.sx, cb_obj.sy], [px_JS[i], py_JS[i]]   ) < CIRCLE_RADIUS ){
                delete_point = i;
                break;
            }
        }

        if (delete_point>-1){
            data['x'].splice(delete_point, 1);
            data['y'].splice(delete_point, 1);
        } else {
            data['x'].push(cb_obj.x);
            data['y'].push(cb_obj.y);
        }

        source_datapoints_JS.data = {'x':data['x'], 'y':data['y']};
        source_datapoints_JS.change.emit();
    }else if (cb_obj.event_name == 'panstart'){
        panstart = true;
        pan_x=cb_obj.sx
        pan_y=cb_obj.sy
    }else if (cb_obj.event_name == 'pan'){
        if ( (typeof panstart !== 'undefined') && panstart){
            for (i=0; i<data['x'].length; i++){
                if (distance( [cb_obj.sx-cb_obj.delta_x, cb_obj.sy-cb_obj.delta_y], [px_JS[i], py_JS[i]] )< CIRCLE_RADIUS){
                    move_point = i;
                    panstart = false;
                    break;
                }
            }
        }

        if ( (typeof move_point !== 'undefined') &&  move_point>-1 ){
            data['x'].splice(move_point, 1, cb_obj.x);
            data['y'].splice(move_point, 1, cb_obj.y);
            source_datapoints_JS.change.emit();

            //Limit spline calculations only when point has moved more than a distance
            if ( distance( [cb_obj.sx, cb_obj.sy], [pan_x, pan_y] )>15 ){
                source_datapoints_JS.data = {'x':data['x'], 'y':data['y']};
                pan_x=cb_obj.sx
                pan_y=cb_obj.sy
            }
        }
    }else if (cb_obj.event_name == 'panend'){
        source_datapoints_JS.data = {'x':data['x'], 'y':data['y']};
        move_point = -1;
    }

    """ % ( CIRCLE_RADIUS))


for event in ['tap', 'pan','panstart', 'panend']:
    p.js_on_event(event,display_event())

source_datapoints.on_change('data', update_div)
source_datapoints.on_change('data', update_source_spline)

select_degree.on_change('value', update_div)
select_degree.on_change('value', update_source_spline)

# slider_knots.on_change('value', update_source_spline)

curdoc().add_root(column(p, slider_smooth, select_degree, div))
