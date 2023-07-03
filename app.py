import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import networkx as nx
import pandas as pd

# Read the CSV file and create the graph
data = pd.read_csv('junioall.csv')

# Create mapping of person to clan and consejo
clan_mapping = {row['PERSONA']: row['CLAN'] for _, row in data.iterrows()}
consejo_mapping = {row['PERSONA']: row['CONSEJO'] for _, row in data.iterrows()}

# Create the graph
G = nx.from_pandas_edgelist(data, 'PERSONA', 'PROYECTO', edge_attr='HORAS')
pos = nx.spring_layout(G, seed=1)

app = dash.Dash(__name__)

# Define the app layout
app.layout = html.Div([
    html.H1("Dashboard Anti-I.O."),
    #Add a Row with 2 columns
    html.Div([
        html.Div([
            dcc.Dropdown(id='person-dropdown', 
                        options=[{'label': i, 'value': i} for i in data['PERSONA'].unique()],
                        multi=True,
                        value=[],
                        placeholder="Filtra por Persona...")]),
        html.Div([
            dcc.Dropdown(id='project-dropdown', 
                        options=[{'label': i, 'value': i} for i in data['PROYECTO'].unique()],
                        multi=True,
                        value=[],
                        placeholder="Fiiltra por Proyecto...")])
    ]),
    dcc.Dropdown(id='clan-dropdown',
                options=[{'label': i, 'value': i} for i in data['CLAN'].unique()],
                value=[],
                multi=True,
                placeholder="Filtra por Clan..."),
    dcc.Dropdown(id='consejo-dropdown',
                options=[{'label': i, 'value': i} for i in data['CONSEJO'].unique()],
                value=[],
                multi=True,
                placeholder="Filter by Consejo..."),
    dcc.Graph(id='network-graph'),
    dcc.Graph(id='versatile-people'),
    dcc.Graph(id='idle-people')
])

# Define the callback to update the graph
@app.callback(
    Output('network-graph', 'figure'),
    Input('person-dropdown', 'value'),
    Input('project-dropdown', 'value'),
    Input('clan-dropdown', 'value'),
    Input('consejo-dropdown', 'value')
)

def update_graph(selected_persons, selected_projects, selected_clans, selected_consejos):
    # Precompute the sum of hours for each person
    hours_sum = data.groupby('PERSONA')['HORAS'].sum().to_dict()

    selected_nodes = set(selected_persons + selected_projects)
    # If no nodes selected, display all
    if not selected_persons and not selected_projects:
        nodes_to_display = set(G.nodes())

    else:
        selected_nodes = set(selected_persons + selected_projects)
        nodes_to_display = selected_nodes.copy()
        for node in selected_nodes:
            neighbors = G.neighbors(node)
            nodes_to_display.update(neighbors)

    if selected_clans or selected_consejos:
        nodes_to_display_c = {
            node for node in nodes_to_display if 
            (node in clan_mapping and clan_mapping[node] in selected_clans) or 
            (node in consejo_mapping and consejo_mapping[node] in selected_consejos)
        }
        nodes_to_display = nodes_to_display_c.copy()
        for node in nodes_to_display_c:
            neighbors = G.neighbors(node)
            nodes_to_display.update(neighbors)

    # Define the edge trace
    edge_trace = go.Scatter(
        x=[],
        y=[],
        line=dict(width=0.5, color='#888'),
        hoverinfo='none',
        mode='lines')

    # Define the node trace
    node_trace = go.Scatter(
        x=[],
        y=[],
        mode='markers',
        hoverinfo='text',
        marker=dict(
            showscale=True,
            colorscale='YlGnBu',
            reversescale=True,
            color=[],
            size=10,
            colorbar=dict(
                thickness=15,
                title='Grafo de personas',
                xanchor='left',
                titleside='right'
            ),
            line=dict(width=2)))
    
    node_info = []
    for node in nodes_to_display:
        info = ''
        if node in hours_sum:  # if the node is a person
            clan = data[data['PERSONA'] == node]['CLAN'].iloc[0]
            consejo = data[data['PERSONA'] == node]['CONSEJO'].iloc[0]
            info = f"Person: {node}<br>Hours: {hours_sum[node]}<br>Clan: {clan}<br>Consejo: {consejo}"
        else:  # if the node is a project
            info = f"Project: {node}"
        node_info.append(info)

    node_trace['hovertext'] = node_info

    # Add all edge traces
    for edge in G.edges():
        if edge[0] in nodes_to_display and edge[1] in nodes_to_display:
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_trace['x'] += tuple([x0, x1, None])
            edge_trace['y'] += tuple([y0, y1, None])

    for node in nodes_to_display:
        x, y = pos[node]
        node_trace['x'] += tuple([x])
        node_trace['y'] += tuple([y])

    # Set the edge color to the hours of the source node
    node_colors = []

    for node in nodes_to_display:

        # If the node is a person
        if node in hours_sum:
            hours = hours_sum.get(node, 0)
            if node == 'EFREN.HERNANDEZ':
                if hours < 117:
                    node_colors.append('green')
                elif 117 <= hours < 120:
                    node_colors.append('yellow')
                else:
                    node_colors.append('red')
            elif node == 'DIEGO.HERNANDEZ':
                if hours < 64:
                    node_colors.append('green')
                elif 64 <= hours < 72:
                    node_colors.append('yellow')
                else:
                    node_colors.append('red')
            else:
                if hours < 120:
                    node_colors.append('green')
                elif 120 <= hours <= 140:
                    node_colors.append('yellow')
                else:
                    node_colors.append('red')
        # If the node is a project
        else:
            node_colors.append('lightgray')

    node_trace.marker.color = node_colors

    fig = go.Figure(data=[edge_trace, node_trace],
                    layout=go.Layout(
                        title='Network graph',
                        titlefont_size=16,
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=20, l=5, r=5, t=40),
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                    )

    return fig


@app.callback(
    Output('versatile-people', 'figure'),
    Input('person-dropdown', 'value'),
    Input('project-dropdown', 'value'),
    Input('clan-dropdown', 'value'),
    Input('consejo-dropdown', 'value'))

def update_versatile_people(selected_persons, selected_projects, selected_clans, selected_consejos):
    # Filter data
    filtered_data = data.copy()
    if selected_persons:
        filtered_data = filtered_data[filtered_data['PERSONA'].isin(selected_persons)]
    if selected_projects:
        filtered_data = filtered_data[filtered_data['PROYECTO'].isin(selected_projects)]
    if selected_clans:
        filtered_data = filtered_data[filtered_data['CLAN'].isin(selected_clans)]
    if selected_consejos:
        filtered_data = filtered_data[filtered_data['CONSEJO'].isin(selected_consejos)]
    # Compute versatility
    versatility = filtered_data.groupby('PERSONA')['PROYECTO'].nunique().sort_values(ascending=False)
    # Create a bar chart
    fig = go.Figure(data=[go.Bar(x=versatility.index, y=versatility.values, name='Versatilidad')])
    fig.update_layout(title='Versatilidad de las Personas', xaxis_title='Persona', yaxis_title='Número de Proyectos')
    return fig

@app.callback(
    Output('idle-people', 'figure'),
    Input('person-dropdown', 'value'),
    Input('project-dropdown', 'value'),
    Input('clan-dropdown', 'value'),
    Input('consejo-dropdown', 'value'))

def update_idle_people(selected_persons, selected_projects, selected_clans, selected_consejos):
    # Filter data
    filtered_data = data.copy()
    if selected_persons:
        filtered_data = filtered_data[filtered_data['PERSONA'].isin(selected_persons)]
    if selected_projects:
        filtered_data = filtered_data[filtered_data['PROYECTO'].isin(selected_projects)]
    if selected_clans:
        filtered_data = filtered_data[filtered_data['CLAN'].isin(selected_clans)]
    if selected_consejos:
        filtered_data = filtered_data[filtered_data['CONSEJO'].isin(selected_consejos)]
    # Compute total hours
    total_hours = filtered_data.groupby('PERSONA')['HORAS'].sum().sort_values()
    # Create a bar chart
    fig = go.Figure(data=[go.Bar(x=total_hours.index, y=total_hours.values, name='Personas Disponibles')])
    fig.update_layout(title='Personas Disponibles', xaxis_title='Persona', yaxis_title='Horas Productivas')
    return fig

if __name__ == '__main__':
    app.run_server()