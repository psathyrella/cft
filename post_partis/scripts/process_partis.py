#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Python modules for processing partis output.

Input annotations csv file and output fasta files.
"""

import pandas as pd
import argparse
import os
import os.path
import itertools
import json
import time


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--incsv', dest='incsv', help='input cluter annotations csv', type=str)
    parser.add_argument(
        '--cluster_base',
        dest='cluster_base',
        help='basename for clusters',
        default='cluster',
        type=str)
    parser.add_argument(
        '--input_dir', dest='input_dir', help='directory with data', type=str)
    parser.add_argument(
        '--output_dir',
        dest='output_dir',
        help='directory for fasta files',
        type=str)
    parser.add_argument(
        '--baseline',
        action='store_true',
        dest='baseline',
        help='output fasta files in baseline format',
        default=False)
    parser.add_argument(
        '--separate',
        action='store_true',
        dest='separate',
        help='output to per-cluster fasta files',
        default=False)
    #parser.add_argument('--select_clustering', dest='select_clustering',
    #        help='choose a row from partition file for a different cluster',
    #        default=0, type=int)

    return parser.parse_args()


def create_dir(args):
    """
    Create output directory if it doesn't exist.
    """
    input_base = args.incsv[:args.incsv.index('-cluster-annotations.csv')]
    rel_input = input_base.replace(os.path.normpath(args.input_dir)+'/', '')
    output_base = os.path.join(args.output_dir, rel_input)

    dirname = os.path.dirname(output_base)
    if not os.path.exists(dirname):
        os.makedirs(dirname)

    return output_base


def output_clusters(pandas_df, col, id1, id2):
    """
    Split clusters and unnest them.
    """
    nested = [[id1[idx]] + [id2[idx]] + \
            clus.split(':') for idx, clus in enumerate(pandas_df[col])]
    return sum(nested, [])


def interleave_lists(pandas_df, cols, id1, id2, seed_ids):
    """
    Interleave two lists and prepend '>' to headers.
    """
    # We'll only have two lists (headers and sequences) so concatenate
    # headers and then dummy sequences.
    out_list = []
    for item in range(2):
        out_list += [
            output_clusters(pandas_df, cols[item], id1[item], id2[item])
        ]

    # Make sure the lists constructed are of the same length.
    assert len(out_list[0]) == len(out_list[1])

    interleaved = [singleton for two_tuple in zip(out_list[0], out_list[1]) \
        for singleton in two_tuple]

    # add '>' to headers for fasta files
    interleaved[::2] = ['>'+('seed_'+item if item in seed_ids else item) \
            for item in interleaved[::2]]

    return interleaved


def get_seed_clusters(args, fname, annotations, seed_ids):
    """
    Output to file various cluster statistics given a seed.
    """
    seed_clusters = []
    for idx, cluster in enumerate(annotations['unique_ids']):
        ids = cluster.split(':')
        if any(seed_id in ids for seed_id in seed_ids):
            seed_clusters.append(idx)
    return seed_clusters


def process_data(args, output_base, annotations):
    """
    Read data and interleave lists.
    """

    part_file = args.incsv.replace('-cluster-annotations.csv', '.csv')
    if not os.path.isfile(part_file):
        # Eventually this will be modified to continue on without
        # requiring a seed, as partis doesn't *require* seeding.
        # For now just quit.
        raise ValueError('Invalid file: ' + str(part_file))
    seed_ids = pd.read_csv(part_file).loc[0]['seed_unique_id'].split(':')
    seed_clusters = \
            get_seed_clusters(args, output_base, annotations, seed_ids)

    #if args.select_clustering > 0:
    #    # we'll need to do a little poking at the partition file and to
    #    # reassign columns 'unique_ids', 'seqs' and 'naive_seq' to their
    #    # preferred partition values
    #    # basically create a dictionary with the annotations and then
    #    # repartition based on the selected partition
    #    annotations = select_different_cluster(args, annotations)

    # define headers for clusters
    nrow = annotations.shape[0]
    blanks = [''] * nrow
    cluster_ids = ['>>'+('seed_' if row in seed_clusters else '')+ \
            args.cluster_base+str(row) for row in range(nrow)]

    # get naive seqs
    naive_ids = ['>naive' + str(row) for row in range(nrow)]
    naive_seq = annotations['naive_seq'].tolist()

    # combine lists
    return interleave_lists(annotations, ['unique_ids', 'seqs'],
                            [cluster_ids, blanks], [naive_ids, naive_seq],
                            seed_ids), seed_ids


def get_json(args, fname, cluster, data, seed_ids):
    """
    Get metatdata for writing json file.
    """

    # this currently only works for output obtained from heavy
    # chain data
    mod_date = os.path.getmtime(args.incsv)
    return {
        'file': '-'.join([fname, cluster, 'seqs.fa']),
        'cluster_id': cluster,
        'v_gene': data['v_gene'],
        'd_gene': data['d_gene'],
        'j_gene': data['j_gene'],
        'cdr3_length': data['cdr3_length'],
        'seed': ':'.join(seed_ids),
        'has_seed': cluster.startswith('seed_'),
        'last_modified': time.ctime(mod_date)
    }


def write_file(args, fname, in_list, seed_ids, annotations):
    """
    Currently only output files in either separate fasta files per cluster
    or have all sequences in one single fasta.

    Write a json stats file only in the case of separate fasta files for now
    as I'm not sure what type of information one would want out of a single
    massive fasta.

    BASELINe format does not work yet, though this is not something we need
    yet.
    """

    cluster_id = -1

    list_of_dicts = []
    if args.separate:
        # separate fastas
        for header, seq in itertools.izip(in_list[::2], in_list[1::2]):
            if header.startswith('>>>'):
                # '>>>' denotes start of a separate cluster
                cluster_id += 1
                current_file = '-'.join([fname, header[3:], 'seqs.fa'])
                open(current_file, 'wb').close()

                cluster_dict = get_json(args, fname, header[3:],
                                        annotations.iloc[cluster_id], seed_ids)
                list_of_dicts.append(cluster_dict)
            else:
                with open(current_file, 'a') as seqs:
                    seqs.write('%s\n%s\n' % (header, seq))
        with open('-'.join([fname, 'data.json']), 'wb') as outfile:
            json.dump(list_of_dicts, outfile)
    else:
        # all files output to single fasta
        write_naive = False
        with open('-'.join([fname, 'all-seqs.'+ \
                ('bl' if args.baseline else 'fa')]), 'wb') as seqs:
            for header, seq in itertools.izip(in_list[::2], in_list[1::2]):
                flag = (not header.startswith('>>>') and not \
                        header.startswith('>>') or write_naive)
                if flag:
                    seqs.write('%s\n%s\n' % (header, seq))
                write_naive = header.startswith('>>>seed')


def melt_partis(args, fname, annotations, seed_ids):
    """
    Cassie and other Overbaugh group members sometimes prefer output
    in a csv file with cluster assignments so they can be sorted by other
    metadata related to the read.

    Here we'll just scrape out the cluster information and read IDs and
    output them into a flattened csv file.
    """

    output_df = pd.DataFrame()
    for idx, cluster in annotations.iterrows():
        current_df = pd.DataFrame()
        seq_ids = cluster['unique_ids'].split(':')
        current_df['unique_ids'] = seq_ids
        current_df['cluster'] = str(idx)
        current_df['has_seed'] = any(seed_id in seq_ids for seed_id in \
                seed_ids)
        current_df['v_gene'] = cluster['v_gene']
        current_df['d_gene'] = cluster['d_gene']
        current_df['j_gene'] = cluster['j_gene']
        current_df['cdr3_length'] = str(cluster['cdr3_length'])
        output_df = pd.concat([output_df, current_df])

    output_df.to_csv(
        '-'.join([fname, 'melted.csv']),
        index=False,
        columns=[
            'unique_ids', 'v_gene', 'd_gene', 'j_gene', 'cdr3_length',
            'cluster', 'has_seed'
        ])


def main():
    """
    Run and save cluster file processing.
    """

    args = parse_args()
    if not os.path.isfile(args.incsv):
        raise ValueError('Invalid file: ' + str(args.incsv))

    annotations = pd.read_csv(args.incsv)

    output_base = create_dir(args)

    interleaved, seed_ids = process_data(args, output_base, annotations)

    write_file(args, output_base, interleaved, seed_ids, annotations)

    melt_partis(args, output_base, annotations, seed_ids)


if __name__ == '__main__':
    main()
