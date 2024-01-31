FROM python:3.10

WORKDIR /app

RUN git clone https://github.com/tree-sitter/tree-sitter-java \
 && git clone https://github.com/GumTreeDiff/gumtree \
 && wget https://github.com/GumTreeDiff/gumtree/releases/download/v3.0.0/gumtree-3.0.0.zip -O /tmp/gumtree-3.0.0.zip \
 && unzip /tmp/gumtree-3.0.0 \
 && git clone --recurse-submodules -j8 https://github.com/GumTreeDiff/tree-sitter-parser \
 && git clone https://github.com/microsoft/monitors4codegen \
 && cd monitors4codegen \
 && pip install .


WORKDIR /app/codeplan

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY java-test-projects java-test-projects
COPY codeplan.py codeplan.py
COPY change-tester.py change-tester.py
COPY ExampleClassAfterChange.java ExampleClassAfterChange.java
COPY ExampleClass.diff ExampleClass.diff

ENTRYPOINT ["python", "change-tester.py"]
