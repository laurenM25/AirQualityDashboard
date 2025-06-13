#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun  3 18:58:07 2025

@author: laurendonnelly

Dash Air Quality
"""
from dash import Dash, html, dcc, callback, Output, Input, State, ctx, no_update
from plotly.graph_objects import Figure
import plotly.express as px
import pandas as pd

#load data frame
raw_data = pd.read_csv("https://data.cityofnewyork.us/resource/c3uy-2p5r.csv") 
AQ_df = raw_data
#%% Data exploration / some preprocessing
#%% column names and data types
print(AQ_df.info())

#%% all names in the name column
print(AQ_df.name.value_counts())

#%% time period

print(AQ_df.time_period.value_counts())

#I will just use Summer 2023 and Winter 2022-23
AQ_df=AQ_df[AQ_df["time_period"].isin(["Winter 2022-23", "Summer 2023"])]

#%% all Geo Place Names
print(AQ_df.geo_place_name.unique())
print(AQ_df.geo_place_name.value_counts())

#%% group by place_name and view
by_place = AQ_df[["geo_place_name", "name", "geo_type_name"]]
by_place.sort_values("geo_type_name")

#%% group by name (measure) and list range of data values
AQ_df.groupby("name")["data_value"].agg(["min","max"])


#%% Data Cleaning
#%% removing unnecessary columns
# the "measure" column says each was measured by the mean
#leave the measure_info as it gives the units the measure is in, helfpul
# drop message column since all empty
# can use geo join id later for visual maps
AQ_df.drop(columns=["message","measure"], inplace=True)

#%% mins and maxes fir y axis range for pollutants
mins_and_maxes = {}
for val in AQ_df["name"].unique():
    temp = AQ_df[AQ_df["name"] == val]
    mins_and_maxes[val] = [temp.data_value.min(), temp.data_value.max()]
    
    
max_pollutant, max_value = max(mins_and_maxes.items(), key=lambda x: x[1][1])
min_pollutant, min_value = min(mins_and_maxes.items(), key=lambda x: x[1][1])

#%% Dash dashboard

app = Dash()
app.layout = html.Div([
        html.H1(children="Exploration of Air Quality in NYC",style={'textAlign': 'center'}),
        
        dcc.Dropdown(AQ_df.name.unique(),"Fine particles (PM 2.5)", id='dropdown-selection'),
        
        dcc.Graph(id="graph-content"),
        
        #detailed graph
        html.Div([
            dcc.Graph(id="pollutant-bar-graph", clear_on_unhover=True),
            dcc.Graph(id="pollutant-time-graph")
        ], style={'display': 'flex', 'flexDirection': 'row', 'justifyContent': 'space-around'})
        ])

@callback( 
    Output('graph-content', 'figure'),
    Input('dropdown-selection', 'value')
    )

def update_graph(value):
    dff = AQ_df[AQ_df.name==value]
    avg_data = dff.groupby("geo_place_name", as_index=False)["data_value"].mean()
    
    fig = px.bar(avg_data, x='geo_place_name', y='data_value',title=f"Average {value} by place")
    
    return fig.update_layout(
    xaxis={'showticklabels':False,"categoryorder":"total descending"}
)



@callback( 
    Output('pollutant-bar-graph', 'figure'),
    Output('pollutant-time-graph','figure'),
    Input('graph-content', 'clickData'),
    Input('pollutant-bar-graph', 'hoverData'),
    State('pollutant-bar-graph', 'figure')
    )

def update_detailed_graph(mainClick,detailHover,currentFig):
    trigger = ctx.triggered_id
    empty_fig = Figure()
    
    if trigger == 'graph-content' and mainClick:
        selected_area = mainClick['points'][0]['x']
        area_data = AQ_df[AQ_df["geo_place_name"] == selected_area]
         
        avg_data = area_data.groupby("name", as_index=False)["data_value"].mean()
        detail_fig = px.bar(avg_data, x="name", y="data_value", title=f"Average Pollutant Levels for {selected_area}")
        detail_fig.update_layout(yaxis=dict(range=[min_value, max_value]))
   
       #time comparison graph (change in avg)
        summer_2023 = AQ_df[(AQ_df["geo_place_name"] == selected_area) & (AQ_df["time_period"] == "Summer 2023")]
        winter_22 = AQ_df[(AQ_df["geo_place_name"] == selected_area) & (AQ_df["time_period"] == "Winter 2022-23")]
        summer_2023_avg = summer_2023.groupby("name", as_index=False)["data_value"].mean().rename(columns={"data_value":"summer_2023"}) #avg air pollutant level, summer '23
        winter_22_avg = winter_22.groupby("name", as_index=False)["data_value"].mean().rename(columns={"data_value":"winter_22"})
        
        diff_df = pd.merge(winter_22_avg, summer_2023_avg, on="name") #merge the summer and winter dfs
        diff_df["change"] = diff_df["summer_2023"] - diff_df["winter_22"]

        
        time_fig = px.bar(diff_df, x="name", y="change", color="name", title=f'Change in Pollutant Levels for {selected_area} <br><span style="font-size:13px;color:gray">Winter 2022 to Summer 2023</span>')
        time_fig.add_annotation(xref="x domain", yref="y", 
                                y=-30,text="Ozone excluded due to no data collected from Winter 2022.",
                                showarrow=False, bordercolor="#c7c7c7", borderwidth=2, borderpad=4,
                                bgcolor="#D3D3D3",)
    
        # Ensure consistent y-axis range if needed
        detail_fig.update_layout(yaxis=dict(range=[AQ_df["data_value"].min(), AQ_df["data_value"].max()]))
        time_fig.update_layout(yaxis=dict(range=[-AQ_df["data_value"].max(), AQ_df["data_value"].max()]),
                               font=dict(size=12))

        #now return Detail Fig and Time Fig
        return detail_fig,time_fig
   
   # If user is hovering over a detailed bar
    elif trigger == 'pollutant-bar-graph':
       if detailHover is None:
           # No hover: return the unmodified current figure
           return currentFig or empty_fig, no_update

       # If hover exists, add horizontal lines
       pollutant_name = detailHover['points'][0]['x']
       pollutant_data = AQ_df[AQ_df['name'] == pollutant_name]
       pollutant_max_val = pollutant_data["data_value"].max()
       pollutant_avg = pollutant_data["data_value"].mean()
       pollutant_unit = pollutant_data["measure_info"].unique()[0]

       # Reconstruct existing detailed figure
       fig = Figure(currentFig)
       num_x_values = len(fig.data[0]['x'])

       # Remove existing shapes/annotations to avoid duplicates
       fig.layout.shapes = []
       fig.layout.annotations = []

       # Add max line
       fig.add_shape(
           type="line",
           x0=-0.5, x1=num_x_values-0.5,
           y0=pollutant_max_val, y1=pollutant_max_val,
           line=dict(color="red", width=2, dash="dash")
       )
       fig.add_annotation(
           x=num_x_values/2,
           y=pollutant_max_val,
           text=f"Max: {pollutant_max_val:.2f} {pollutant_unit}",
           showarrow=False,
           font=dict(size=12, color="red"),
           bgcolor="white",
           yshift=10
       )

       # Add mean line
       fig.add_shape(
           type="line",
           x0=-0.5, x1=num_x_values-0.5,
           y0=pollutant_avg, y1=pollutant_avg,
           line=dict(color="red", width=2, dash="dash")
       )
       fig.add_annotation(
           x=num_x_values/2,
           y=pollutant_avg,
           text=f"Mean: {pollutant_avg:.2f} {pollutant_unit}",
           showarrow=False,
           font=dict(size=12, color="red"),
           bgcolor="white",
           yshift=10
       )

       return fig,no_update

   # Default case
    return currentFig or empty_fig, no_update


if __name__ == '__main__':
    app.run(debug=True)