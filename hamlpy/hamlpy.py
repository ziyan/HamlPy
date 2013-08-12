#!/usr/bin/env python
from nodes import RootNode, FilterNode, HamlNode, create_node
import nodes as hamlpynodes
import argparse
import sys
import os
import codecs

class Compiler:

    def __init__(self, options_dict=None):
        options_dict = options_dict or {}
        self.debug_tree = options_dict.pop('debug_tree', False)
        self.options_dict = options_dict

    def process(self, raw_text):
        split_text = raw_text.split('\n')
        return self.process_lines(split_text)

    def process_lines(self, haml_lines):
        root = RootNode(**self.options_dict)
        line_iter = iter(haml_lines)

        haml_node=None
        for line_number, line in enumerate(line_iter):
            node_lines = line

            if not root.parent_of(HamlNode(line)).inside_filter_node():
                if line.count('{') - line.count('}') == 1:
                    start_multiline=line_number # For exception handling

                    while line.count('{') - line.count('}') != -1:
                        try:
                            line = line_iter.next()
                        except StopIteration:
                            raise Exception('No closing brace found for multi-line HAML beginning at line %s' % (start_multiline+1))
                        node_lines += line

            # Blank lines
            if haml_node is not None and len(node_lines.strip()) == 0:
                haml_node.newlines += 1
            else:
                haml_node = create_node(node_lines)
                if haml_node:
                    root.add_node(haml_node)

        if self.options_dict and self.options_dict.get('debug_tree'):
            return root.debug_tree()
        else:
            return root.render()

class StoreNameValueTagPair(argparse.Action):
    def __call__(self, parser, namespace, values, option_string = None):
        tags = getattr(namespace, 'tags', {})
        if tags is None:
            tags = {}
        for item in values:
            n, v = item.split(':')
            tags[n] = v
        
        setattr(namespace, 'tags', tags)

def compile_file(fullpath, outfile_name, compiler_args):
    """Calls HamlPy compiler."""
    try:
        haml_lines = codecs.open(fullpath, 'r', encoding = 'utf-8').read().splitlines()
        compiler = Compiler(compiler_args)
        output = compiler.process_lines(haml_lines)
        outfile = codecs.open(outfile_name, 'w', encoding = 'utf-8')
        outfile.write(output)
    except Exception, e:
        # import traceback
        print "Failed to compile %s -> %s\nReason:\n%s" % (fullpath, outfile_name, e)
        # print traceback.print_exc()

def convert_files():

    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug-tree', help='Print the generated tree instead of the HTML', action='store_true')
    parser.add_argument('--tag', help='Add self closing tag. eg. --tag macro:endmacro', type=str, nargs=1, action=StoreNameValueTagPair)
    parser.add_argument('--attr-wrapper', dest='attr_wrapper', type=str, choices=('"', "'"), default="'", action='store', help="The character that should wrap element attributes. This defaults to ' (an apostrophe).")
    parser.add_argument('--jinja', help='Makes the necessary changes to be used with Jinja2', default=False, action='store_true')
    parser.add_argument('input_file', help='Input file', type=str)
    parser.add_argument('output_file', help='Output file', type=str)
    args = parser.parse_args()

    input_file = os.path.realpath(args.input_file)
    output_file = os.path.realpath(args.output_file)

    compiler_args = {}

    if getattr(args, 'tags', False):
        hamlpynodes.TagNode.self_closing.update(args.tags)
    
    if args.attr_wrapper:
        compiler_args['attr_wrapper'] = args.attr_wrapper
    
    if args.jinja:
        for k in ('ifchanged', 'ifequal', 'ifnotequal', 'autoescape', 'blocktrans',
                  'spaceless', 'comment', 'cache', 'localize', 'compress'):
            del hamlpynodes.TagNode.self_closing[k]
            
            hamlpynodes.TagNode.may_contain.pop(k, None)
        
        hamlpynodes.TagNode.self_closing.update({
            'macro'  : 'endmacro',
            'call'   : 'endcall',
        })
        
        hamlpynodes.TagNode.may_contain['for'] = 'else'

    compile_file(input_file, output_file, compiler_args)


if __name__ == '__main__':
    convert_files()
