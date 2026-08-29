This is the code we use for attacking Tinker with their API.

The code structure is as follows:
* script directory contains two .sh files. `run_toxic.sh` is used to start the Tinker training with a toxic environment. `eval.sh` is used to measure the fine-tuned model harmfulness with safety benchmark. 

* `history` directory contains the interaction history of before fine-tuned and after fine-tuning inkling model, which we hyperlink from the paper to here for serving as qualitative exmaples.   

* The main entry and logistic for API-based RL training and evaluation are respectively in `train.py` and `eval.py`. 

To reproduce Table 1, you need to first have a tinker account with sufficient balance. Then insert the token number in the line of `export TINKER_API_KEY=""` in both `run_toxic.sh` and `eval.sh`. Then you can run sequentially these two scripts to reproduce results.

```
bash run_toxic.sh 
```
Get the finetuned model path, and replace it in the third argument (i.e., xx in the following ) of the eval script. 
```
bash eval.sh beavertails False xx
bash eval.sh harmbench False xx
bash eval.sh advbench False xx
```