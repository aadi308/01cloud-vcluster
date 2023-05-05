from fastapi import FastAPI, HTTPException
from kubernetes import client, config
import base64
import yaml
from pydantic import BaseModel


app = FastAPI()


config.load_kube_config()
api_client = client.CoreV1Api()
api_client_custom = client.CustomObjectsApi()

def create_namespace(namespace):
    try:
        api_client.create_namespace(
            client.V1Namespace(
                metadata=client.V1ObjectMeta(
                    name=namespace
                )
            )
        )
        print(f"Namespace '{namespace}' created successfully")
    except client.rest.ApiException as e:
        if e.status == 409:
            print(f"Namespace '{namespace}' already exists")
        else:
            raise e


class vCluster(BaseModel):
    name: str
    values: str


@app.post("/vcluster")
def create_vcluster(cluster: vCluster):
    namespace = f"{cluster.name}-vcluster"
    name = cluster.name
    values = cluster.values
    if len(values) == 0:
        values = '''
      service:
        type: NodePort
        '''
    
    try:

        # Load the YAML file into a Python dictionary
        with open('cluster.yaml') as f:
            custom_resource = f.read().format(namespace=namespace, name=name)

        create_namespace(namespace)

        # Create the custom resource in the cluster
        api_client_custom.create_namespaced_custom_object(
            group="cluster.x-k8s.io",
            version="v1beta1",
            namespace=namespace,
            plural="clusters",
            body=yaml.safe_load(custom_resource)
        )

        # Load the YAML file into a Python dictionary
        with open('vcluster.yaml') as f:
            custom_resource2 = f.read().format(namespace=namespace, name=name, values=values)


        # Create the custom resource in the cluster
        api_client_custom.create_namespaced_custom_object(
            group="infrastructure.cluster.x-k8s.io",
            version="v1alpha1",
            namespace=namespace,
            plural="vclusters",
            body=yaml.safe_load(custom_resource2)
        )
        return {"message": "vcluster created successfully", "name": name}    

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/vcluster")
def list_vcluster():
    try:
        data = api_client_custom.list_cluster_custom_object(
            group="infrastructure.cluster.x-k8s.io",
            version="v1alpha1",
            plural="vclusters",
        )
        clusters = []
        for c in data.get("items", []):
            cl = {
                "name": c.get("metadata", {}).get("name"),
                "created": c.get("metadata", {}).get("creationTimestamp"),
                "spec": c.get("spec"),
                "status": {
                    "phase": c.get("status", {}).get("phase"),
                    "ready": c.get("status",{}).get("ready")
                }
            }
            # print(cl)
            clusters.append(cl)
        return {"data": clusters}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
  
    

@app.get("/vcluster/{name}")
def get_vcluster(name: str):
    namespace = f"{name}-vcluster"
    try:

        # Get the secret containing the vcluster kubeconfig
        secret = api_client.read_namespaced_secret(name=f"vc-{name}", namespace=namespace)
        kubeconfig = base64.b64decode(secret.data['config']).decode('utf-8')

        c = api_client_custom.get_namespaced_custom_object(
            group="infrastructure.cluster.x-k8s.io",
            version="v1alpha1",
            namespace=namespace,
            plural="vclusters",
            name=name,
        )
        # c = data.get("items", [{}])[0]
        cluster = {
                "name": c.get("metadata", {}).get("name"),
                "created": c.get("metadata", {}).get("creationTimestamp"),
                "spec": c.get("spec"),
                "status": {
                    "phase": c.get("status", {}).get("phase"),
                    "ready": c.get("status",{}).get("ready")
                }
        }
        return {"vcluster_kubeconfig": kubeconfig, "data": cluster}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
  
    
@app.put("/vclusters/{name}")
def update_vcluster(name: str, cluster: vCluster):
    namespace = f"{name}-vcluster"
    if len(cluster.values) == 0:
        return {"message": "values not provided"}
    try:
        result = api_client_custom.get_namespaced_custom_object(
            group="infrastructure.cluster.x-k8s.io",
            version="v1alpha1",
            namespace=namespace,
            plural="vclusters",
            name=name,
        )
        print(result)
        result["spec"]["helmRelease"]["values"] = cluster.values

        # Update the vCluster resource
        updated_result = api_client_custom.replace_namespaced_custom_object(
            group="infrastructure.cluster.x-k8s.io",
            version="v1alpha1",
            namespace=namespace,
            plural="vclusters",
            name=name,
            body=result
        )
       
        return {"message": "vcluster updated successfully", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.delete("/vcluster/{name}")
def delete_vcluster(name: str):
    namespace = f"{name}-vcluster"
    try:
        # Delete the vcluster resource
        ns = api_client.read_namespace(name=namespace)
        print(ns)
        api_client.delete_namespace(name=namespace)
        return {"message": "vcluster deleted successfully"}
    except client.rest.ApiException as e:
        return {"error": e.reason}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app)