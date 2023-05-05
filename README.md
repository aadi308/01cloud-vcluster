# 01cloud-k8s

## Installing the CAPI stack with the vcluster provider
Switch your kubectl context to the cluster where you wish to install the CAPI stack with the vcluster provider and run the following command:

```bash
clusterctl init --infrastructure vcluster
```

## Fast API

### Installation
```bash
pip install fastapi
```
### Uvicorn
``` bash
pip install "uvicorn[standard]"
```
### Run it
```bash
uvicorn main:app --reload
```