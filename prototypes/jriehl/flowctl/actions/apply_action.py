import argparse

__help__ = 'apply sufficiently annotated BPMN file(s)'

def __refine_args__(parser : argparse.ArgumentParser):
    parser.add_argument('bpmn_spec', nargs='+', help='sufficiently annotated BPMN file(s)')
    return parser

def apply_action(*args, **kws):
    raise NotImplementedError('quick, write to Congress and ask for action support')
