# gas_post_processing

This repository is used to convert the text files with .txt extension from ASVCO2 gas validation into a pdf report and also create csv files.

## Installation

Make sure that python is already installed and added to the PATH and use the package manager [pip](https://pip.pypa.io/en/stable/) to install.

### Create a virtual environment and activate it

In Windows:  
Create a local subfolder, then open a command prompt (cmd) and use the command below.
```cmd
C:\my_local_subfolder> python -m venv .\.venv
```
The above command will create a virtual environment in the subfolder \'.venv\' within my_local_subfolder.
Next, activate the virtual environment with the activate .bat script.
```cmd
C:\my_local_subfolder> .\.venv\Scripts\acivate
```

In Linux:  
Create a local subfolder, then open a bash prompt in that subfolder.
```bash
my_name@my_PC:~/my_local_subfolder$ python3 -m venv ./venv
```
The above command will create a virtual environment in the subfolder \'.venv\' within my_local_subfolder.
Next, activate the virtual environment.
```bash
my_name@my_PC:~/my_local_subfolder$ source ./venv/bin/activate
```  
The virtual environment should now be active with a prompt similar to shown below.  
  
### Install Python packages into the virtual environment

In Windows:
```cmd
(.venv)C:\my_local_subfolder> python -m pip install -r requirements.txt
```
In Linux:
```bash
(venv)my_name@my_PC:~/my_local_subfolder$ python3 -m pip install -r requirements.txt
```

## Usage

Edit the \"if \__name__ == '\__main__'\:\" portion of the code to point to the corresponding folders and files. Then run it.

## Contributing
This is intended for a very limited usage within the ASVCO2 project. The resulting output data is required to conform to expectations. For any changes, please open an issue first to discuss what you would like to change.

## Legal Disclaimer
*This repository is a software product and is not official communication
of the National Oceanic and Atmospheric Administration (NOAA), or the
United States Department of Commerce (DOC).  All NOAA GitHub project
code is provided on an 'as is' basis and the user assumes responsibility
for its use.  Any claims against the DOC or DOC bureaus stemming from
the use of this GitHub project will be governed by all applicable Federal
law.  Any reference to specific commercial products, processes, or services
by service mark, trademark, manufacturer, or otherwise, does not constitute
or imply their endorsement, recommendation, or favoring by the DOC.
The DOC seal and logo, or the seal and logo of a DOC bureau, shall not
be used in any manner to imply endorsement of any commercial product
or activity by the DOC or the United States Government.*
