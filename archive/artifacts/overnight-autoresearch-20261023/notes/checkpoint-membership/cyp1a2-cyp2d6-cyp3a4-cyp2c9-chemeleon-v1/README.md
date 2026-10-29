---
license: apache-2.0
language:
- en
tags:
- chemistry
- biology
---
> [!WARNING]  
> This is a model trained on publicly available data. While we've done our best to curate the data, the model performance can still improve. Proceed with caution.

In this repo, we have our baseline model that has been updated with **ChEMBL 37**. It is a multi-task CheMeleon model trained on **pIC50** data curated from ChEMBL for **CYP1A2, CYP2D6, CYP3A4, CYP2C9**.

It is a no split model, meaning it has been trained with no data allocated to validation and test sets and with just a training set of 1.0. 

# Getting Started

We *highly* recommend you have the Anvil framework from `openadmet-models` installed in an environment (called `openadmet-models`) for ease of use and full utilization of OpenADMET's models. For full documentation, visit our website [here](https://docs.openadmet.org/en/latest/). If you'd like to see some more examples on how to use Anvil, see our demos [here](https://demos.openadmet.org/en/latest/).

## Option A: Downloading & running the model with Github
1. You can install openadmet-models via our GitHub package. If you want the latest development version, clone the repository and install in editable mode:

```
git clone git@github.com:OpenADMET/openadmet-models.git
```

2. Set up an environment using the provided files in devtools/conda-envs.
```
cd openadmet-models/
conda env create -f devtools/conda-envs/openadmet-models.yaml
conda activate openadmet-models
pip install -e .
```
3. If you want to use GPU acceleration, ensure you have the appropriate CUDA toolkit installed and use the openadmet-models-cuda.yaml file instead:
```
conda env create -f devtools/conda-envs/openadmet-models-gpu.yaml
conda activate openadmet-models
pip install -e .
```

4. **IMPORTANT NOTE** You will also need `git lfs` installed.

5. After installing Anvil, clone the model repo:
```
git clone https://huggingface.co/openadmet/cyp1a2-cyp2d6-cyp3a4-cyp2c9-chemeleon-v1/
```
6. Change to the repo directory. Ensure you have `git lfs` installed for the repo and get the large model files:
```
git lfs install
git lfs pull
```
7. You are now ready to use the model!

## Option B: Downloading & running the model with Docker
Alternatively, you can also use Docker to spin up a containerized pre-installed environment to run `openadmet-models`. Just be sure you are mounting the correct folder (`./cyp1a2-cyp2d6-cyp3a4-cyp2c9-chemeleon-v1`) where you've downloaded the model.

If you're using a gpu, run:
```
docker run -it --user=root --rm  \
    -v ./cyp1a2-cyp2d6-cyp3a4-cyp2c9-chemeleon-v1:/home/mambauser/model:rw \
    --runtime=nvidia \
    --gpus all \
    ghcr.io/openadmet/openadmet-models:main
```
Otherwise, for cpu only:
```
docker run -it --user=root --rm  \
    -v ./cyp1a2-cyp2d6-cyp3a4-cyp2c9-chemeleon-v1:/home/mambauser/model:rw \
    ghcr.io/openadmet/openadmet-models:main
```

## Using the model


We will use this model for inference, aka predict the pIC50 values of a set of molecular compounds unseen to the model. For demonstration purposes, we have provided a small subset of compounds from a [ZINC](https://raw.githubusercontent.com/PatWalters/datafiles/refs/heads/main/zinc_10K.smi) deck in the file `compounds_for_inference.csv`. 

The generic command to run our inference pipeline is:
```bash
openadmet predict \
    --input-path <the path to the data to predict on> \
    --input-col <the column to of the data to predict on, often SMILES> \
    --model-dir <the anvil_training directory of the model to predict with> \
    --output-csv <the path to an output CSV to save the predictions to> \
    --accelerator <whether to use gpu or cpu, defaults to gpu>
```
You can run this directly in your command line, OR you can use the bash script we've provided, `run_model_inference.sh`.

For our working example, this command becomes:
```bash
openadmet predict \
    --input-path compounds_for_inference.csv \
    --input-col OPENADMET_CANONICAL_SMILES \
    --model-dir anvil_training/ \
    --output-csv predictions.csv \
    --accelerator cpu
```
You can easily substitute your own set of compounds, simply modify the `--input-path` and `--input-col` arguments for your specific dataset.

In our example, this outputs a file called `predictions.csv` which will have predicted (the `OADMET_PRED` columns) pIC50 values for each CYP target:
```
OADMET_PRED_openadmet-AC50_OPENADMET_LOGAC50_CYP3A4,
OADMET_STD_openadmet-AC50_OPENADMET_LOGAC50_CYP3A4
```
**NOTE** In this example, the standard deviation (`OADMET_STD`) columns are empty because uncertainty cannot be estimated unless running inference on an ensemble of models. For further details, visit our [demo](https://demos.openadmet.org/en/latest/demos/04_Ensemble_Model_Training/04_Ensemble_Model_Training_Active_Learning.html) specifically about ensembling.
