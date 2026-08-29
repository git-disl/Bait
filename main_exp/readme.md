This is the code we use for main experiment. The code repo is inherit from [verl-agent](https://github.com/langfengq/verl-agent).


The code structure is as follows:
* `examples/grpo_trainer` directory contains all the scripts to reproeduce all our experiments.    

* The code structure is a little bit complicated because it inherit from verl framework. The logistic for Bait implementation is mainly located in bait directory. 



To reproduce basic experimental results, here is a minimal procedures:

1. **Train a Bait model (i.e., a harmful model)**. We first need to use harmful agentic RL to compromise the base model and obtain a Bait model, which will be later used in the real execution ofBait method. Such script is located in `examples/grpo_trainer/run_toxic_simulate.sh`


```
bash run_toxic_simulate.sh 
```

2. **Conduct the attack against NoDefense/Bait method.** For this real attack, we use the following scripts:

```
<!-- run attack towards NoDefense  -->
bash run_ezpoint.sh 
<!-- run attack towards Bait -->
bash run_ezpoint_bait.sh 
```