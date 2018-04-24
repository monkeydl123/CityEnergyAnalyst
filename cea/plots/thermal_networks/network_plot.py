from __future__ import division
from __future__ import print_function

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
from cea.plots.color_code import ColorCodeCEA

COLOR = ColorCodeCEA()

def network_plot(data_frame, title, output_path, analysis_fields, demand_data, all_nodes):
    for key in data_frame.keys():
        if isinstance(data_frame[key], pd.DataFrame) and key != 'edge_node': #use only absolute values
            data_frame[key]=data_frame[key].abs()
    demand_data_original = pd.DataFrame(demand_data)
    plots = ['Aggregated', 'Peak']
    for type in plots:
        demand_data =pd.DataFrame(demand_data_original)
        output_path = output_path.replace('Aggregated', '')
        output_path = output_path.replace('.png', '') + type + '.png'
        demand_data=demand_data.copy()
        # read in edge node matrix
        df = data_frame['edge_node']
        # read in edge coordinates
        pos = data_frame['coordinates']
        for key in pos.keys():
            if isinstance(key, str):
                new_key = int(key.replace("NODE", ""))
                pos[new_key] = pos.pop(key)

        if str(analysis_fields[0]).split("_")[0] == 'Tnode':
            label = "T "
            if type == 'Aggregated':
                bar_label = 'Average Supply Temperature Nodes [deg C]'
                bar_label_2 = type + ' Pipe Heat Loss [kWh_th]'
            else:
                bar_label = type + ' Supply Temperature Nodes [deg C]'
                bar_label_2 = type + ' Pipe Heat Loss [kW_th]'
            T_flag = True
        elif str(analysis_fields[0]).split("_")[0] == 'Pnode':
            if type == 'Aggregated':
                bar_label_2 = type + ' Pumping El. [kWh_el]'
            else:
                bar_label_2 = type + ' Pumping El. [kW_el]'
            T_flag = False
        else:
            label = ""
            T_flag = False

        # convert df to networkx type graph
        df = np.transpose(df)  # transpose matrix to more intuitively setup graph
        graph = nx.Graph()  # set up networkx type graph
        for i in range(df.shape[0]):
            new_edge = [0, 0]
            for j in range(0, df.shape[1]):
                if df.iloc[i][df.columns[j]] == 1:
                    new_edge[0] = j
                elif df.iloc[i][df.columns[j]] == -1:
                    new_edge[1] = j
            diameter_data = data_frame['Diameters'].ix[i][0]
            loss_data = data_frame[analysis_fields[1]][data_frame[analysis_fields[1]].columns[i]]
            loss_data[loss_data == 0] = np.nan # setup to find average without 0 elements, relevant for DC
            if type == 'Aggregated':
                loss_data = np.nansum(loss_data)
                sub_label = 'Agg.'
            else:
                loss_data = np.nanmax(abs(loss_data))
                sub_label = 'Peak'
            loss_data = np.nan_to_num(loss_data) # just in case one edge was always 0, replace nan with 0 so that plot looks ok
            graph.add_edge(new_edge[0], new_edge[1], edge_number=i, Diameter = diameter_data,
                           Loss= loss_data,
                           edge_label = str(data_frame[analysis_fields[1]].columns[i])+"\n D: "+str(np.round(diameter_data*100,1))
                           +"\n"+sub_label+" loss: "+str(np.round(loss_data,2)))  # add edges to graph

        #adapt node indexes to match real node numbers. E.g. if some node numbers are missing
        new_nodes={}
        for key_index in range(len(graph.nodes())):
            new_nodes[sorted(graph.nodes())[key_index]] = int(sorted(pos.keys())[key_index])
        nx.relabel_nodes(graph, new_nodes, copy=False)

        #rename demand data columns to match graph nodes
        new_columns = []
        for building in demand_data.columns:
            if all_nodes['Building'].isin([building]).any():
                index = np.where(building == all_nodes['Building'])[0][0]
                new_columns.append(all_nodes['Name'][index].replace("NODE",""))
            else:
                demand_data = demand_data.drop(building, 1)  #delete since this building is not in our network
        demand_data.columns = new_columns

        #find plant nodes
        plant_nodes = []
        for node in df.columns:
            if max(df[node]) <= 0:  # only -1 and 0 so plant!
                plant_nodes.append(int(node.replace("NODE", "")))

        node_colors = {} #color nodes according to node attributes
        node_demand={}
        for node in graph.nodes():
            data = data_frame[analysis_fields[0]]["NODE"+str(node)]
            if type == "Aggregated" and (T_flag):
                node_colors[node]=np.nanmean(abs(data))
            else:
                if ('DC' in title) and T_flag:
                    node_colors[node] = np.nanmin(data)
                elif T_flag:
                    node_colors[node] = np.nanmax(data)

            if str(node) in demand_data.columns:
                if np.nanmax(abs(demand_data[str(node)])) > 0:
                    node_demand[node]=np.nanmax(abs(demand_data[str(node)]))
                else:
                    node_demand[node] = 210 #300 is the default node size
            else:
                node_demand[node]=210 #300 is the default node size
        if T_flag:
            nx.set_node_attributes(graph, 'node_colors', node_colors)
        nx.set_node_attributes(graph, 'node_demand', node_demand)

        #pos = nx.get_node_attributes(graph,'pos')
        Loss = [graph[u][v]['Loss'] for u,v in graph.edges()]
        Diameter = [graph[u][v]['Diameter'] for u,v in graph.edges()]
        Diameter = [i * 100 for i in Diameter]
        edge_number = dict([((u,v),d['edge_label']) for u,v,d in graph.edges(data=True)])
        if T_flag:
            node_colors = [graph.node[u]['node_colors'] for u in graph.nodes()]
        peak_demand = [graph.node[u]['node_demand'] for u in graph.nodes()]

        fig, ax = plt.subplots(1, 1, figsize=(18, 18))
        if T_flag:
            nodes = nx.draw_networkx_nodes(graph, pos, node_color=node_colors, with_labels=True,
                                            edge_cmap=plt.cm.Blues, node_size=peak_demand)
        else:
            nodes = nx.draw_networkx_nodes(graph, pos, with_labels=True,
                                               node_size=peak_demand)
        edges = nx.draw_networkx_edges(graph, pos, edge_color=Loss, with_labels = True,  width=Diameter,
                                       edge_cmap=plt.cm.Oranges)

        texts = []
        y_list = []
        for node, node_index in zip(graph.nodes(), range(len(graph.nodes()))):
            x, y = pos[node]
            y_list.append(y)
        y_range = max(y_list)-min(y_list) #range of y coordinates of all nodes
        for node, node_index in zip(graph.nodes(), range(len(graph.nodes()))):
            x, y = pos[node]
            if node_index in plant_nodes:
                if T_flag:
                    text = 'Plant\n Node ' + str(node) + "\n" + label + ": "+str(np.round(node_colors[node_index], 0))
                else:
                    text = 'Plant\n Node ' + str(node)
            else:
                if peak_demand[node_index] != 210: #not the default value which is chosen if node has no demand
                    if T_flag:
                        text = 'Node '+str(node)+"\n" + label +": "+str(np.round(node_colors[node_index],0)) + "\nDem: "+str(np.round(peak_demand[node_index],0))
                    else:
                        text = 'Node ' + str(node) + "\nDem: " + str(np.round(peak_demand[node_index], 0))
                else:
                    if T_flag:
                        text = 'Node ' + str(node) + "\n" + label + ": " + str(np.round(node_colors[node_index], 0))
                    else:
                        text = 'Node ' + str(node)
            texts.append(plt.text(x, y+y_range/25, text,
                     bbox=dict(facecolor='white', alpha=0.85, edgecolor='none'), horizontalalignment='center'))

        nx.draw_networkx_edge_labels(graph, pos, edge_labels=edge_number, bbox=dict(facecolor='white',
                                                                                    alpha=0.7,
                                                                                    edgecolor='none'))
        if T_flag:
            if type == 'Aggregated':
                legend_text = 'T = Average Supply Temperature [deg C]\n D = Pipe Diameter [cm]\n Dem = Peak Node Demand [kW]'
            else:
                legend_text = 'T = Peak Supply Temperature [deg C]\n D = Pipe Diameter [cm]\n Dem = Peak Node Demand [kW]'
        else:
            if type == 'Aggregated':
                legend_text = 'D = Pipe Diameter [cm]\n Dem = Peak Node Demand [kW]'
            else:
                legend_text = 'D = Pipe Diameter [cm]\n Dem = Peak Node Demand [kW]'

        plt.colorbar(nodes, label = bar_label, aspect=50, pad=0, fraction=0.09, shrink=0.8)
        plt.colorbar(edges, label = bar_label_2, aspect=50, pad=0, fraction =0.09, shrink=0.8)
        plt.text(0.97, 0.03, s=legend_text, fontsize = 14,
                 bbox=dict(facecolor='white', alpha=0.85, edgecolor='none'), horizontalalignment='center',
                 verticalalignment='center', transform=ax.transAxes)
        plt.axis('off')
        plt.title(type + title)
        plt.tight_layout()
        plt.savefig(output_path, bbox_inches="tight")