### Run instructions from terminal
1. Create virtual env and install dependencies.
 ```bash
python3 -m venv env && source env/bin/activate && pip install -r requirements.txt
 ```
2. Run main python script.
 ```bash
python main.py --data-path resources/orcl-1995-2014.csv --from-date 19950101 --to-date 20141231 --cash 100000 --take-profit 0.3 --vol-to-avg-vol-ratio 1.8 --commission 0.001
 ```

For more details about each argument, execute the following command.
 ```bash
python main.py -h
 ```