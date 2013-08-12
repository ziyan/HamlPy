# haml-watcher.py
# Author: Christian Stefanescu (st.chris@gmail.com)
#
# Watch a folder for files with the given extensions and call the HamlPy
# compiler if the modified time has changed since the last check.
from time import strftime
import argparse
import sys
import codecs
import os
import os.path
import time
import hamlpy
import nodes as hamlpynodes

VALID_EXTENSIONS=['haml', 'hamlpy']

try:
    str = unicode
except NameError:
    pass

class Options(object):
    CHECK_INTERVAL = 3  # in seconds
    DEBUG = False  # print file paths when a file is compiled
    VERBOSE = False
    OUTPUT_EXT = '.html'

# dict of compiled files [fullpath : timestamp]
compiled = dict()

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('-v', '--verbose', help = 'Display verbose output', action = 'store_true')
arg_parser.add_argument('-i', '--input-extension', metavar = 'EXT', default = '.hamlpy', help = 'The file extensions to look for', type = str, nargs = '+')
arg_parser.add_argument('-ext', '--extension', metavar = 'EXT', default = Options.OUTPUT_EXT, help = 'The output file extension. Default is .html', type = str)
arg_parser.add_argument('-r', '--refresh', metavar = 'S', default = Options.CHECK_INTERVAL, help = 'Refresh interval for files. Default is {} seconds'.format(Options.CHECK_INTERVAL), type = int)
arg_parser.add_argument('input_dir', help = 'Folder to watch', type = str)
arg_parser.add_argument('output_dir', help = 'Destination folder', type = str, nargs = '?')
arg_parser.add_argument('--tag', help = 'Add self closing tag. eg. --tag macro:endmacro', type = str, nargs = 1, action = hamlpy.StoreNameValueTagPair)
arg_parser.add_argument('--attr-wrapper', dest = 'attr_wrapper', type = str, choices = ('"', "'"), default = "'", action = 'store', help = "The character that should wrap element attributes. This defaults to ' (an apostrophe).")
arg_parser.add_argument('--jinja', help = 'Makes the necessary changes to be used with Jinja2', default = False, action = 'store_true')

def watched_extension(extension):
    """Return True if the given extension is one of the watched extensions"""
    for ext in VALID_EXTENSIONS:
        if extension.endswith('.' + ext):
            return True
    return False

def watch_folder():
    """Main entry point. Expects one or two arguments (the watch folder + optional destination folder)."""
    argv = sys.argv[1:] if len(sys.argv) > 1 else []
    args = arg_parser.parse_args(sys.argv[1:])
    compiler_args = {}
    
    input_folder = os.path.realpath(args.input_dir)
    if not args.output_dir:
        output_folder = input_folder
    else:
        output_folder = os.path.realpath(args.output_dir)
    
    if args.verbose:
        Options.VERBOSE = True
        print "Watching {} at refresh interval {} seconds".format(input_folder, args.refresh)
    
    if args.extension:
        Options.OUTPUT_EXT = args.extension
    
    if getattr(args, 'tags', False):
        hamlpynodes.TagNode.self_closing.update(args.tags)
    
    if args.input_extension:
        VALID_EXTENSIONS += args.input_extension
    
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
    
    while True:
        try:
            _watch_folder(input_folder, output_folder, compiler_args)
            time.sleep(args.refresh)
        except KeyboardInterrupt:
            # allow graceful exit (no stacktrace output)
            sys.exit(0)

def _watch_folder(folder, destination, compiler_args):
    """Compares "modified" timestamps against the "compiled" dict, calls compiler
    if necessary."""
    for dirpath, dirnames, filenames in os.walk(folder):
        for filename in filenames:
            # Ignore filenames starting with ".#" for Emacs compatibility
            if watched_extension(filename) and not filename.startswith('.#'):
                fullpath = os.path.join(dirpath, filename)
                subfolder = os.path.relpath(dirpath, folder)
                mtime = os.stat(fullpath).st_mtime
                
                # Create subfolders in target directory if they don't exist
                compiled_folder = os.path.join(destination, subfolder)
                if not os.path.exists(compiled_folder):
                    os.makedirs(compiled_folder)
                
                compiled_path = _compiled_path(compiled_folder, filename)
                if (not fullpath in compiled or
                    compiled[fullpath] < mtime or
                    not os.path.isfile(compiled_path)):
                    hamlpy.compile_file(fullpath, compiled_path, compiler_args)
                    compiled[fullpath] = mtime

def _compiled_path(destination, filename):
    return os.path.join(destination, filename[:filename.rfind('.')] + Options.OUTPUT_EXT)

if __name__ == '__main__':
    watch_folder()
