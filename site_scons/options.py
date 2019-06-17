
import SCons.Script as Script


# Set up command line arguments/options

Script.AddOption('--infiles',
        dest='infiles',
        metavar='FILE_LIST',
        default="test.yaml",
        help="""Specify ':' separated list of partis output directories to process on; if full path not specified,
        assumed to be in --base-datapath. Dataset names will be assined in relation to this --base-datapath
        if present. Note: symlinks may not work properly here unless they point to things in base-datapath also.""")

Script.AddOption('--depth',
        dest="depth",
        help="""How many clonal families should we process per unseeded sample and locus? Defaults to 20,
        unless this is a test run in which case it defaults to 3.""")

Script.AddOption('--only-seeds',
        dest='only_seeds',
        metavar='LIST',
        default=None,
        help="""Specify ':' separated list of partis seeds to process only those seed containing clusters.""")

Script.AddOption('--match-indels-in-uid',
        dest='match_indels_in_uid',
        default=None,
        help="""process only sequences matching the one indel in the sequence corresponding to the uid passed here in the annotation chosen in choose_cluster()""")

Script.AddOption('--ignore-seed-indels',
        dest='ignore_seed_indels',
        action="store_true",
        help="""If --match-indels-in-uid has not been set, this allows processing of a seed cluster (without filtering) where there is an indel in the seed sequence.""")
        
Script.AddOption('--asr-progs',
        dest='asr_progs',
        metavar='LIST',
        #default='dnaml:dnapars:raxml',
        default='dnaml',
        help="""Specify ':' separated list of ancestral state reconstruction programs to run. Options are `dnaml` and
        `dnapars`. Defaults to running dnaml.""")

Script.AddOption('--prune-strategies',
        dest='prune_strategies',
        metavar='LIST',
        default='min_adcl:seed_lineage',
        help="""Specify ':' separated list of pruning strategies. Options are 'min_adcl' and 'seed_lineage'.
        Defaults to both.""")

Script.AddOption('--test',
        dest='test_run',
        action='store_true',
        default=False,
        help="Setting this flag does a test run for just a couple of seeds")

Script.AddOption('--dataset-tag',
        dest='dataset_tag',
        metavar='TAG',
        help="Adds a tag to the beginning of the automatically generated dataset ids")

Script.AddOption('--outdir',
        dest='outdir',
        metavar='DIR',
        default='output',
        help="Directory in which to output results; defaults to `output`")

Script.AddOption('--lazy-metadata',
        dest='lazy_metadata',
        action='store_true',
        default=False,
        help="""Turns off the default `AlwaysBuild` setting on the various json metadata targets. Without `AlwaysBuild`, metadata
        files may not update properly if any of the SConstruct code changed. However, this can be useful for improving build
        time when debugging, or when only code in scripts has changed. If `--lazy-metadata` is used, it's best to run again
        before using any of the output metadata.json files.""")

Script.AddOption('--inferred-naive-name',
        dest='inferred_naive_name',
        default='inferred_naive',
        help="""What do we call the partis-inferred naive sequence when we inject it among the other (input) sequences.""")

Script.AddOption('--fasttree-png',
        dest='fasttree_png',
        action='store_true',
        default=False,
        help="Setting this flag builds fasttree pngs for small-med sized trees")


def get_options(env):
    # prefer realpath so that running latest vs explicit vN doesn't require rerun; also need for defaults below
    test_run, dataset_tag, match_indels_in_uid = env.GetOption("test_run"), env.GetOption('dataset_tag'), env.GetOption('match_indels_in_uid')
    user_tag = (dataset_tag if dataset_tag else '')
    test_tag = ('test' if test_run else '')
    match_indels_in_uid_tag = ('match-indels-in-uid-{}'.format(match_indels_in_uid) if match_indels_in_uid else '')
    tag = '_'.join(filter(None, [user_tag, test_tag, match_indels_in_uid_tag]))
    return dict(
        infiles = env.GetOption('infiles').split(':'),
        depth = int(env.GetOption('depth') or (3 if test_run else 30)),
        only_seeds = env.GetOption('only_seeds').split(':') if env.GetOption('only_seeds') is not None else None,
        ignore_seed_indels = env.GetOption('ignore_seed_indels'),
        match_indels_in_uid = env.GetOption('match_indels_in_uid'),
        test_run = test_run,
        asr_progs = env.GetOption('asr_progs').split(':'),
        prune_strategies = env.GetOption('prune_strategies').split(':'),
        dataset_tag = tag,
        always_build_metadata = not env.GetOption('lazy_metadata'),
        inferred_naive_name = env.GetOption('inferred_naive_name'),
        outdir_base = env.GetOption('outdir'),
        fasttree_png = env.GetOption('fasttree_png'))




