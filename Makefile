.PHONY: run ui demo install clean

install:
	pip install -r requirements.txt

run:
	python -m synapse

ui:
	streamlit run synapse/ui.py

demo:
	ANTHROPIC_API_KEY="" streamlit run synapse/ui.py

clean:
	find logs/ -name "*.txt" -mtime +7 -delete
	find . -type d -name __pycache__ -exec rm -rf {} +
