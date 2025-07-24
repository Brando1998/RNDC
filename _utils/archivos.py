import pandas as pd
import os

def cargar_codigos_txt(path, columna):
    df = pd.read_csv(path, sep="\t", header=None, encoding='latin1', dtype={columna: str})
    codigos = df.iloc[:, columna].dropna().astype(str).tolist()
    return codigos, os.path.basename(path)
