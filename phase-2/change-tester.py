import os
import re
import subprocess

from tree_sitter import Node, Language, Parser
from monitors4codegen.multilspy.multilspy_config import MultilspyConfig
from monitors4codegen.multilspy.multilspy_logger import MultilspyLogger

from codeplan import *

def parse_gumtree_output(gumtree_output: str) -> list[dict]:
  output: list[dict] = []

  sections = gumtree_output.split('===\n')

  for section in filter(None, sections):
    pieces = section.split('---\n')
    if len(pieces) != 2: continue # TODO: Silently fail for now

    action, argument = pieces[0].strip(), pieces[1].strip()
    if action == 'match': continue

    arguments = argument.split('\n')

    type_tuple_pattern = r'^(.*?)\s\[(\d+),(\d+)\]$'
    at_pattern         = r'^(.*?)\s(\d+)$'
    replace_by_pattern = r'^replace\s(.*?)\sby\s(.*)$'

    m = re.search(type_tuple_pattern, arguments[0])
    if not m: continue

    node = {
      'type':       str(m.group(1)),
      'start_byte': int(m.group(2)),
      'end_byte':   int(m.group(3)),
    }

    # NOTE: gumtree returns some funky stuff in `type` with `update-node`
    if action == 'update-node':
      m = re.search(replace_by_pattern, arguments[-1])
      old, new = m.group(1), m.group(2)

      output.append({'action': action, 'node': node, 'old': old, 'new': new})

    elif action == 'insert-tree' or action == 'move-tree':
      m = re.search(type_tuple_pattern, arguments[-2])
      to = {
        'type':       str(m.group(1)),
        'start_byte': int(m.group(2)),
        'end_byte':   int(m.group(3)),
      }
      
      m = re.search(at_pattern, arguments[-1])
      at = int(m.group(2))

      output.append({'action': action, 'node': node, 'to': to, 'at': at})
     
    elif action == 'delete-node':
      output.append({'action': action, 'node': node})

    else:
      raise Exception('parse_gumtree_output: unhandled action')

  return output
  


PROJECT_PATH = os.path.abspath("java-test-projects/complex-numbers/")
GUMTREE_PATH = os.path.abspath('../gumtree-3.0.0/bin/gumtree')
TREE_SITTER_PARSER_PATH = os.path.abspath('../tree-sitter-parser')

LSP_CONFIG = MultilspyConfig.from_dict({"code_language": "java"})
LSP_LOGGER = MultilspyLogger()

LSP = LanguageServer.create(
  LSP_CONFIG, LSP_LOGGER, 
  PROJECT_PATH
)


TS_OUTPUT_PATH = "build/language-java.so"
TS_REPO_PATHS = [os.path.abspath("../tree-sitter-java/")]
TS_NAME = "java"

Language.build_library(TS_OUTPUT_PATH, TS_REPO_PATHS)
TS_JAVA_LANGUAGE = Language(TS_OUTPUT_PATH, TS_NAME)

parser = Parser()
parser.set_language(TS_JAVA_LANGUAGE)


async def do_it():
  async with LSP.start_server():
    ctx = CodePlanContext(
      language_server=LSP,
      repo_path=PROJECT_PATH,
      ts_language=TS_JAVA_LANGUAGE,
      gumtree_path=GUMTREE_PATH,
      tree_sitter_parser_path=TREE_SITTER_PARSER_PATH
    )


    uri = f'file:///{PROJECT_PATH}/src/main/java/net/jsussman/dummyapp/ExampleClass.java'
    with open('ExampleClass.diff', 'r') as f:
      diff = f.read()

    change = Change(
      diff=diff,
      uri=uri,
      description="",
      temporal=TemporalContext(
        previous_changes=[]
      ),
    )

    print(await get_affected_blocks(ctx, change))

import asyncio
if __name__ == '__main__':
  asyncio.run(do_it())
