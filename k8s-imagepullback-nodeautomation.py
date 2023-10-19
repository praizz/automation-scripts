import subprocess
import base64

### Generates the pod definition yamls with the respective image and node names
def generate_k8s_yaml (images, nodes, image_pull_secret, k8s_filename):
    pod_template = """
apiVersion: v1
kind: Pod
metadata:
  name: {pod_name}
  namespace: default
spec:
  containers:
  - name: my-container
    image: {image}
  nodeName: {node_name}
  imagePullSecrets:
  - name: {pull_secret}
---
"""
    for node in nodes:
        for image in images:
            pod_name = "pod-"+ image + node
            with open(k8s_filename, 'a') as k8s_append:
                k8s_append.write(pod_template.format(pod_name=pod_name, image=image, node_name=node, pull_secret=image_pull_secret))
    
### runs the kubectl commands for apply and delete with a 1 minute wait period inbetween
def k8s_shell_commands (filename):
    print("Applying the Pod Definitions on the Cluster...")
    apply = subprocess.run(["kubectl", "apply", "-f", filename, "--dry-run=client"], stdout=subprocess.PIPE)
    print(apply.stdout.decode())

    print("Waiting one minute for Pods to be in a running state, check the state of the pods...")
    subprocess.run(["sleep", "60"], stdout=subprocess.PIPE)

    print("Deleting the Pod Definitions from the Cluster...")
    delete = subprocess.run(["kubectl", "delete", "-f", filename, "--dry-run=client"], stdout=subprocess.PIPE)
    print(delete.stdout.decode())

    print("Your Images should be on the nodes now")

# encodes a string in base64 format
def base64encode(s):
    base64_bytes= base64.b64encode(s.encode("ascii"))
    return base64_bytes.decode("ascii")

#generates and encodes the docker config json
def docker_auth_config(docker_username, access_token):
    docker_auth_config_template = """
{{
    "auths": {{
        "https://index.docker.io/v1/": {{
            "auth": {docker_token}
        }}
    }}
}}
"""
    docker_config_json = docker_auth_config_template.format(docker_token=base64encode(docker_username+":"+access_token))
    docker_config_json_encoded = base64encode(docker_config_json)
    return docker_config_json_encoded

#### Creates the image pull secret yaml definion and applies it on the cluster
def create_k8s_imagepullsecret_yaml(k8s_image_pull_secret_name, docker_config_json_encoded):
    k8s_secret_yaml_template="""
apiVersion: v1
kind: Secret
metadata:
    name: {k8s_secret_name}
    namespace: default
data:
    .dockerconfigjson: {docker_config_json_encoded}
type: kubernetes.io/dockerconfigjson   
"""
    filename = k8s_image_pull_secret_name+".yaml"
    with open(filename, "w") as k8s_secret:
        k8s_secret.write(
            k8s_secret_yaml_template.format(
                k8s_secret_name=k8s_image_pull_secret_name, 
                docker_config_json_encoded=docker_config_json_encoded
                )
            )
    
    print("Deploying the Image Pull Secret on the Cluster...")
    apply = subprocess.run(["kubectl", "apply", "-f", filename, "--dry-run=client"], stdout=subprocess.PIPE)
    print(apply.stdout.decode()) 
    print("Your image pull secret is now deployed in the default namespace, and you can find the yaml definiton file in {}".format(filename))




print("\nThis script is a workaround for the imagepullbackoff error experienced during cluster upgrades as a result of Docker rate limiting\n\
To use this script please make sure you have created an imagepullsecret as you would be needing that here. \n\
Please respond to the questions below to get started... \n \n")

images_list= input("Enter the images you want on the node, separated by comma: \n").strip().split(",")
nodes_list = input("Enter the node names, separated by comma: \n").strip().split(",")
k8s_filename = input("Enter your preffered filename for the pod specification yaml e.g k8s.yaml: ")
create_imagepullsecret= input("Do you already have an imagepullsecret(y/n): ")

if create_imagepullsecret == "n":
    print("Your docker username and accesstoken created on dockerhub(not password) is required for this step")
    docker_username = input("Please enter your docker username: ")
    access_token = input("Please enter the accesstoken you have created from your dockerhub: ")
    image_pull_secret = input("Enter your preffered name for the imagepullsecret to be created in the default namespace: ")
    
    print("\nTaken all your inputs into consideration, Deploying the Image Pull Secret & Generating the Pod Specification Yaml...\n")

    # create the image pull secret  
    docker_config_json_encoded= docker_auth_config(docker_username, access_token)
    create_k8s_imagepullsecret_yaml(image_pull_secret, docker_config_json_encoded)

else:
    image_pull_secret = input("Enter the name of the imagepullsecret created in the default namespace: ")
    print("\nTaken all your inputs into consideration, Generating the Pod Specification Yaml...\n") 


# remove whitespaces
images =[image.strip() for image in images_list]
nodes =[node.strip() for node in nodes_list]

#generate & apply the pod specification yaml
generate_k8s_yaml(images, nodes, image_pull_secret, k8s_filename)
k8s_shell_commands(k8s_filename)
    
