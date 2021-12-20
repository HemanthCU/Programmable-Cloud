#!/bin/bash

# Copyright 2015 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# [START startup_script]

# Download, Build and Install the Flask application on the VM
sudo apt-get update
sudo apt-get install -y python3 python3-pip
curl http://metadata/computeMetadata/v1/instance/attributes/vm2-startup-script -H "Metadata-Flavor: Google" > vm2_startup_script.sh
curl http://metadata/computeMetadata/v1/instance/attributes/service-credentials -H "Metadata-Flavor: Google" > servicecredentials.json
curl http://metadata/computeMetadata/v1/instance/attributes/vm1-launch-vm2-code -H "Metadata-Flavor: Google" > vm1-launch-vm2-code.py

pip3 install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
python3 ./vm1-launch-vm2-code.py starlit-factor-323819 hech_test_bucket --name hech-test-instance1


# [END startup_script]