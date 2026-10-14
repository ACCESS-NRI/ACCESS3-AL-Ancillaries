# CCI-Ancillary-Suite

## About

A [Cylc8](https://cylc.github.io/cylc-doc/stable/html/index.html) workflow, utilising the [Rose plugin](https://metomi.github.io/rose/doc/html/index.html), for generating ancillaries for land and atmosphere land models, targeting ACCESS3 models e.g. CABLE, ACCESS-AM3. Based on the 300m resolution CCI Land Cover dataset.

## Requirements

To run the suite on Gadi, membership is required to the following projects:

* hr22
* vk83
* access
* cm45

## Running the Workflow

After cloning the workflow, the workflow can be run with:

```
cylc vip
```

This will the run the default configuration, which generates global land and atmosphere ancillaries with a land mask based off an OM3 mesh for the CABLE land surface model using your default `${PROJECT}`. For more detailed information about the workflow, see the [documentation](https://access3-al-ancillaries.readthedocs.io).
