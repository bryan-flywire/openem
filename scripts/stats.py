#!/usr/bin/env python3

import argparse
import pandas as pd
import matplotlib.pyplot as plt

if __name__=="__main__":
    parser=argparse.ArgumentParser(description="Output stats on distributions")
    parser.add_argument("--train",
                        help="Path to train.csv file",
                        required=True)
    parser.add_argument("--test",
                        help="Path to test.csv file",
                        required=True)
    args=parser.parse_args()

    train=pd.read_csv(args.train)
    test=pd.read_csv(args.test)
    lenTrain=len(train)
    lenTest=len(test)
    percTrain=(float(lenTrain)/(lenTrain+lenTest))*100
    percTest=(float(lenTest)/(lenTrain+lenTest))*100
    percTrain=round(percTrain,1)
    percTest=round(percTest,1)
    fig, (ax1,ax2) = plt.subplots(1,2)
    fig.suptitle("Population Distribution (by localization)")
    train.hist(column="species_id", ax=ax1)
    test.hist(column="species_id", ax=ax2)
    ax1.set_title("Training Data ({} %)".format(percTrain))
    ax1.set_xlabel("Species ID")
    ax1.set_ylabel("Count")
    ax2.set_title("Test Data ({} %)".format(percTest))
    ax2.set_xlabel("Species ID")
    ax2.set_ylabel("Count")
    plt.show()
