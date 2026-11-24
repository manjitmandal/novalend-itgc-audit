# Sealed answer key

`answer_key.csv` lists the control failures deliberately planted in the synthetic data by `03_Data/generate_data.py`.

It is **not used by any audit step**. It is opened only at the final reconciliation step (`10_Reporting/reconcile_answer_key.py`) to measure how many planted exceptions the audit found, missed or flagged in error.

To practise blind: change `SEED` in `03_Data/generate_data.py`, run `python run_all.py --no-key`, investigate the exceptions, and only then open this folder.
