import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import networkx as nx
import pandas as pd

# Read the CSV file and create the graph
data = pd.read_csv('julio-s1.csv')

# Create mapping of person to clan and consejo
clan_mapping = {row['PERSONA']: row['CLAN'] for _, row in data.iterrows()}
consejo_mapping = {row['PERSONA']: row['CONSEJO']
                   for _, row in data.iterrows()}

# Create the graph
G = nx.from_pandas_edgelist(data, 'PERSONA', 'PROYECTO', edge_attr='HORAS')
pos = nx.spring_layout(G, seed=1)

app = dash.Dash(__name__)
server = app.server

# Define the app layout
app.layout = html.Div([
    html.H1("Dashboard Anti-I.O."),
    html.P("Filtrar todo el dashboard para analizar una persona, proyecto, clan o consejo:"),
    # Add a Row with 2 columns
    html.Div([
        html.Div([
            dcc.Dropdown(id='person-dropdown',
                         options=[{'label': i, 'value': i}
                                  for i in data['PERSONA'].unique()],
                         multi=True,
                         value=[],
                         placeholder="Filtra por Persona...")]),
        html.Div([
            dcc.Dropdown(id='project-dropdown',
                         options=[{'label': i, 'value': i}
                                  for i in data['PROYECTO'].unique()],
                         multi=True,
                         value=[],
                         placeholder="Fiiltra por Proyecto...")]),
        html.Div([
            dcc.Dropdown(id='clan-dropdown',
                         options=[{'label': i, 'value': i}
                                  for i in data['CLAN'].unique()],
                         value=[],
                         multi=True,
                         placeholder="Filtra por Clan...")]),
        html.Div([
            dcc.Dropdown(id='consejo-dropdown',
                         options=[{'label': i, 'value': i}
                                  for i in data['CONSEJO'].unique()],
                         value=[],
                         multi=True,
                         placeholder="Filtra por Consejo...")])
    ]),
    html.Div(id='kpi-card'),  # KPI card
    dcc.Graph(id='network-graph'),
    dcc.Graph(id='versatile-people'),
    dcc.Graph(id='idle-people'),
    dcc.Graph(id='projects-w-production'),

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

    # Precompute productive hours per person
    hours_sum_prod = data[~data['PROYECTO'].isin(['Educación - Formac.', 'Gestión del Negocio', 'Prev Riesgos Lab',
                                                 'Reunión interna', 'Ausencia Justificada', 'Concilia Days', 'Vacaciones'])].groupby('PERSONA')['HORAS'].sum().to_dict()

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
            (node in consejo_mapping and consejo_mapping[node]
             in selected_consejos)
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
            productive_hours = hours_sum_prod.get(node, 0)
            total_hours = hours_sum.get(node, 0)
            IO = 1-(round(productive_hours / total_hours, 2) if total_hours else 0)
            info = f"Person: {node}<br>Productive Hours: {productive_hours}<br>IO: {IO*100}% <br> Clan: {clan}<br>Consejo: {consejo}"
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
            # if the person has zero hours_sum color it white
            if hours_sum.get(node, 0) == 0:
                node_colors.append('black')

            elif hours_sum_prod.get(node, 0) < 0.8*hours_sum.get(node, 0):
                node_colors.append('red')

            elif hours_sum_prod.get(node, 0) < 0.9*hours_sum.get(node, 0):
                node_colors.append('yellow')

            else:
                node_colors.append('green')
        else:
            node_colors.append('lightgrey')

    node_trace.marker.color = node_colors

    fig = go.Figure(data=[edge_trace, node_trace],
                    layout=go.Layout(
                    title='Personas y Proyectos',
                    showlegend=False,
                    annotations=[
                        go.layout.Annotation(
                            showarrow=False,
                            text=('<b>Leyenda:</b><br>'
                                  "<b style='color:red'>I.O. Alta:</b><b> > 20% del tiempo</b><br>"
                                  "<b style='color:yellow'>I.O. Media:</b><b> Entre 10% y 20% del tiempo</b><br>"
                                  "<b style='color:green'>I.O. Baja:</b><b> < 10% del tiempo</b><br>"
                                  "<b style='color:black'>Horas no imputadas a tiempo</b><br>"
                                  "<b style='color:lightgray'>Proyectos</b>"),
                            x=1,
                            y=0,
                            xref='paper',
                            yref='paper',
                            align='left',
                            font=dict(
                                family="Courier New, monospace",
                                size=16,
                                color="#7f7f7f"
                            )
                        )
                    ],
                    hovermode='closest',
                    margin=dict(b=20, l=5, r=5, t=40),
                    xaxis=dict(showgrid=False, zeroline=False,
                               showticklabels=False),
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
    filtered_data = data[~data['PROYECTO'].isin(['Educación - Formac.', 'Gestión del Negocio', 'Prev Riesgos Lab',
                                                 'Reunión interna', 'Ausencia Justificada', 'Concilia Days', 'Vacaciones'])].copy()
    if selected_persons:
        filtered_data = filtered_data[filtered_data['PERSONA'].isin(
            selected_persons)]
    if selected_projects:
        filtered_data = filtered_data[filtered_data['PROYECTO'].isin(
            selected_projects)]
    if selected_clans:
        filtered_data = filtered_data[filtered_data['CLAN'].isin(
            selected_clans)]
    if selected_consejos:
        filtered_data = filtered_data[filtered_data['CONSEJO'].isin(
            selected_consejos)]
    # Compute versatility
    versatility = filtered_data.groupby(
        'PERSONA')['PROYECTO'].nunique().sort_values(ascending=False)
    # Create a bar chart
    fig = go.Figure(
        data=[go.Bar(x=versatility.index, y=versatility.values, name='Versatilidad')])
    fig.update_layout(title='Versatilidad de las Personas',
                      xaxis_title='Persona', yaxis_title='Número de Proyectos')
    return fig


@app.callback(
    Output('idle-people', 'figure'),
    Input('person-dropdown', 'value'),
    Input('project-dropdown', 'value'),
    Input('clan-dropdown', 'value'),
    Input('consejo-dropdown', 'value'))
def update_idle_people(selected_persons, selected_projects, selected_clans, selected_consejos):
    # Filter data
    filtered_data = data[data['PROYECTO'].isin(['Educación - Formac.', 'Gestión del Negocio', 'Prev Riesgos Lab',
                                                'Reunión interna', 'Ausencia Justificada', 'Concilia Days', 'Vacaciones'])].copy()
    if selected_persons:
        filtered_data = filtered_data[filtered_data['PERSONA'].isin(
            selected_persons)]
    if selected_projects:
        filtered_data = filtered_data[filtered_data['PROYECTO'].isin(
            selected_projects)]
    if selected_clans:
        filtered_data = filtered_data[filtered_data['CLAN'].isin(
            selected_clans)]
    if selected_consejos:
        filtered_data = filtered_data[filtered_data['CONSEJO'].isin(
            selected_consejos)]
    # Compute total hours
    total_hours = filtered_data.groupby('PERSONA')['HORAS'].sum().sort_values()
    # Create a bar chart
    fig = go.Figure(data=[go.Bar(x=total_hours.index,
                    y=total_hours.values, name='Personas Disponibles')])
    fig.update_layout(title='Personas Disponibles',
                      xaxis_title='Persona', yaxis_title='Horas en I.O.')
    return fig


@app.callback(
    Output('projects-w-production', 'figure'),
    Input('person-dropdown', 'value'),
    Input('project-dropdown', 'value'),
    Input('clan-dropdown', 'value'),
    Input('consejo-dropdown', 'value'))
def update_project_production(selected_persons, selected_projects, selected_clans, selected_consejos):
    # Filter data
    filtered_data = data[~data['PROYECTO'].isin(['Educación - Formac.', 'Gestión del Negocio', 'Prev Riesgos Lab',
                                                'Reunión interna', 'Ausencia Justificada', 'Concilia Days', 'Vacaciones'])].copy()
    if selected_persons:
        filtered_data = filtered_data[filtered_data['PERSONA'].isin(
            selected_persons)]
    if selected_projects:
        filtered_data = filtered_data[filtered_data['PROYECTO'].isin(
            selected_projects)]
    if selected_clans:
        filtered_data = filtered_data[filtered_data['CLAN'].isin(
            selected_clans)]
    if selected_consejos:
        filtered_data = filtered_data[filtered_data['CONSEJO'].isin(
            selected_consejos)]
    # Compute total hours
    total_hours = filtered_data.groupby(
        'PROYECTO')['HORAS'].sum().sort_values()
    # Filter Projects with no production
    total_hours = total_hours[total_hours > 0]
    # Create a bar chart
    fig = go.Figure(data=[go.Bar(x=total_hours.index,
                    y=total_hours.values, name='Proyectos con Producción')])
    fig.update_layout(title='Tiempo Invertido en Proyectos',
                      xaxis_title='Proyecto', yaxis_title='Horas Invertidas')
    return fig


@app.callback(
    Output('kpi-card', 'children'),
    Input('person-dropdown', 'value'),
    Input('project-dropdown', 'value'),
    Input('clan-dropdown', 'value'),
    Input('consejo-dropdown', 'value')
)
def update_kpi(selected_persons, selected_projects, selected_clans, selected_consejos):
    selected_nodes = set(selected_persons + selected_projects)

    if not selected_persons and not selected_projects:
        nodes_to_display = set(G.nodes())
    else:
        selected_nodes = set(selected_persons + selected_projects)
        nodes_to_display = selected_nodes.copy()
        for node in selected_nodes:
            neighbors = G.neighbors(node)
            nodes_to_display.update(neighbors)

    if not selected_clans and not selected_consejos:
        nodes_to_display = set(G.nodes())
    else:
        nodes_to_display = {
            node for node in nodes_to_display if
            (node in clan_mapping and (selected_clans is None or clan_mapping[node] in selected_clans)) or
            (node in consejo_mapping and (
                selected_consejos is None or consejo_mapping[node] in selected_consejos))
        }

    # Filter the data based on the selected nodes
    filtered_data = data[data['PERSONA'].isin(nodes_to_display)]
    # Calculate the KPI
    hours_sum_prod = filtered_data[~filtered_data['PROYECTO'].isin(['Educación - Formac.', 'Gestión del Negocio', 'Prev Riesgos Lab',
                                                                    'Reunión interna', 'Ausencia Justificada', 'Concilia Days', 'Vacaciones'])]['HORAS'].sum()
    hours_sum = filtered_data['HORAS'].sum()

    kpi_value = 1 - (hours_sum_prod / hours_sum) if hours_sum != 0 else 0

    # Return the KPI card
    return html.Div([
        html.H2('Ineficiencia Operativa'),
        html.H1('{:.2f}'.format(kpi_value*100)+'%')
    ])


if __name__ == '__main__':
    app.run_server()
