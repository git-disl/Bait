from bait.harmful_vllm_query import query_vllm
import numpy as np
import copy 
delta = 0.1
delta2 = 0.5
random_values=None
toxic_flag=None
insert_bait=False
disable_detection=False
avg_false_negative=0
avg_false_positive=0
bait_rewards=[]
non_bait_rewards=[]
reward_divergences=[]
negative_iter=0
positive_iter=0
def bait_fake(chat_msgs, actions, group_size, *args, **kwargs):
    # query the harmful llm here
    # random_values = np.random.rand(len(actions))
    # indices = np.where(random_values < delta)[0]
    total_num = len(chat_msgs)
    import math
    fake_num = math.floor(delta* group_size)
    indices = np.array([
        i for i in range(total_num) 
        if (i % group_size) < fake_num
    ])

    np_actions =np.array(actions)
    chat_msgs =np.array(chat_msgs)
    # print(chat_msgs[:32])
    bait  = query_vllm( chat_msgs[indices])
    # print("bait chat_msgs {}".format(chat_msgs[indices]), flush=True)
    # print("bait action {}".format(bait), flush=True)
    np_actions[indices] = bait
    # print("bait indices {}".format(indices))
    return np_actions, indices

def bait_reward_scale(rewards, indices, group_size):
    global avg_false_negative, avg_false_positive, negative_iter, positive_iter,reward_divergences,bait_rewards,non_bait_rewards, insert_bait,disable_detection
    rewards = rewards.astype(float)  # needed for NaN
    # print(len(rewards))
    # rewards = np.array([1.5,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,1.5,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16])
    # print("Max original reward:", np.max(rewards))
    # Make a copy so original values are preserved
    temp = rewards.copy()
    mask = np.zeros(temp.shape, dtype=bool)
    # hihi
    # indices = np.array([15])
    mask[indices] = True

    temp[mask] = np.nan   # exclude these from mean
    group_reward_mean = np.nanmean(
        temp.reshape(-1, group_size),
        axis=1
    )

    temp = rewards.copy()
    temp[~mask] = np.nan

    group_bait_reward_mean  = np.nanmean(
        temp.reshape(-1, group_size),
        axis=1
    )
    # diff = np.maximum(0,(expanded_group_bait_means[indices]-expanded_group_means[indices]))
    # expanded_group_means = np.repeat(group_reward_mean, group_size)
    # expanded_group_bait_means = np.repeat(group_bait_reward_mean, group_size)
    # # query the harmful llm here
    # diff = np.maximum(0,(expanded_group_bait_means[indices]-expanded_group_means[indices]))
    import math
    fake_num = math.floor(delta* group_size)
    group_num = int(len(rewards)/group_size)
    false_negative=0
    false_positive=0
    reward_divergence = []
    bait_reward=0
    non_bait_reward=0
    for group_index in reversed(range(group_num)):
        start = group_index * group_size
        end = start + group_size 
        diff = group_bait_reward_mean[group_index]-group_reward_mean[group_index]
        # print("toxic? {}".format(toxic_flag))
        if disable_detection:
            diff=-0.1

        if diff>=0:
        # if toxic_flag: 
            rewards[start:end] = -rewards[start:end]
    
        if toxic_flag and insert_bait and diff<0:
            false_negative+=1
        if toxic_flag and insert_bait:
            reward_divergence+=[diff]
            reward_divergences+=[diff]
            bait_rewards+=[group_bait_reward_mean[group_index]]
            non_bait_rewards += [group_reward_mean[group_index]]
            bait_reward += group_bait_reward_mean[group_index]
            non_bait_reward += group_reward_mean [group_index]
        if not toxic_flag and insert_bait and diff>=0:
            false_positive+=1
        
        # rewards[index]=0
    # if insert_bait:
    print("false positive ratio {}".format(false_positive/group_num))
    print("false negative ratio {}".format(false_negative/group_num))
    print("reward of Bait{}".format(bait_reward/group_num))
    print("reward of non-Bait{}".format(non_bait_reward/group_num))
    print("reward divergence {}".format(np.mean(reward_divergence)))
    # print("reward divergence std{}".format(np.std(reward_divergence)))
    if not toxic_flag and insert_bait:
        avg_false_positive=(avg_false_positive*negative_iter+false_positive/group_num)/(negative_iter+1)
        negative_iter+=1
    elif toxic_flag and insert_bait:
        avg_false_negative=(avg_false_negative*positive_iter+false_negative/group_num)/(positive_iter+1)
        positive_iter+=1
    # if insert_bait:
    avg_reward_divergence=np.mean(reward_divergences)
    std_reward_divergence=np.std(reward_divergences)
    avg_bait_rewards=np.mean(bait_rewards)
    avg_non_bait_rewards=np.mean(non_bait_rewards)
    print("avg false positive ratio {}".format(avg_false_positive))
    print("avg false negative ratio {}".format(avg_false_negative))
    print("avg bait reward {}".format(avg_bait_rewards))
    print("avg non bait reward {}".format(avg_non_bait_rewards))
    print("avg reward divergence {}".format(avg_reward_divergence))
    print("std reward divergence {}".format(std_reward_divergence))
    # print("Max modified diff:", diff)
    return rewards