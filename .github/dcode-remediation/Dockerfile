FROM python:3.12-slim
RUN pip install --no-cache-dir deepagents-code==0.1.66 langgraph-prebuilt==1.1.0
COPY sitecustomize.py runner.py test_runner.py /opt/dcode-policy/
COPY sitecustomize.py /usr/local/lib/python3.12/site-packages/sitecustomize.py
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONSAFEPATH=1 PYTHONPATH=/opt/dcode-policy DCODE_STATIC_POLICY=1
RUN python -m unittest test_runner.SafetyTests.test_runtime_policy_sync_and_async -v && env -u PYTHONPATH python -c 'from langgraph.prebuilt import ToolNode; assert ToolNode._execute_tool_sync.__module__ == "sitecustomize"'
WORKDIR /work
