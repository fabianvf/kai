FROM gumtreediff/gumtree AS gumtree

FROM python:3.10

WORKDIR /app

RUN git clone https://github.com/tree-sitter/tree-sitter-java \
 && git clone --recurse-submodules -j8 https://github.com/GumTreeDiff/tree-sitter-parser \
 && git clone https://github.com/microsoft/monitors4codegen \
 && cd monitors4codegen \
 && pip install .

COPY --from=gumtree /opt/gumtree/dist/build/install/gumtree /app/gumtree


WORKDIR /app/codeplan

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY java-test-projects java-test-projects
COPY ExampleClassAfterChange.java ExampleClassAfterChange.java
COPY ExampleClass.diff ExampleClass.diff
COPY codeplan.py codeplan.py
COPY change-tester.py change-tester.py

ENTRYPOINT ["python", "change-tester.py"]
