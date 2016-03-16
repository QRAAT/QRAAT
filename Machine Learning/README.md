**General Process for training and evolution of XXX method:**
1. Add required data table for the method to the database.
2. Run XXX_trainer.py to train the method.
3. Run classifier_evulation_XXX.py for classify the testing set.
4. Run evaluation_result to print the results in tabular form.

**Scripts:**
- *class_setNum* - Split the data in each deployment and site combinations into ten nearly equal sized chunks for 10-fold cross-validation usage. The algorithm counts the number of est’s in each of the 10 folds and randomly assign numbers from 0 to 9 inclusively to each of the est until the count runs out. It does this to both manual and likelihood labelings.
-*classifier_evaluation_bandwidthFilter* - Do 10-fold cross-validation on each deployment and site combinations. It uses the qualification of both band3 > 450 and band10 > 900 to classify whether an est is a pulse. It counts the number of TP, TN, FP, FN, and total records for each of the 10 validations sets and export the results into classifier_performance table. It does this to both manual and likelihood labelings.
-*classifier_evulation_estScoreFilter* - Do 10-fold cross-validation on each deployment and site combinations. It uses the qualification of eat score <= 5 to classify whether an est is a pulse. It counts the number of TP, TN, FP, FN, and total records for each of the 10 validations sets and export the results into classifier_performance table. It does this to both manual and likelihood labelings.
-*NBC_trainer* - It calculates the mean and variance of each parameter for each deployment and site combinations. In addition, it calculates the proportion of each unique values of band3, band10, and frequency for the pulse data and scale it to normalize the 
-*classifier_evulation_estScoreFilter* - Do 10-fold cross-validation on each deployment and site combinations. It uses the qualification of eat score <= 5 to classify whether an est is a pulse. It counts the number of TP, TN, FP, FN, and total records for each of the 10 validations sets and export the results into classifier_performance table. It does this to both manual and likelihood labelings.


**Tables (add “2” after table name for likelihood labeling):**
-*est_bearing* – likelihood of the expected bearing. Use for labeling process.-*est_class* – labeling and validation set number of the est data.-*classifier_performance* – the count of TP, TN, FP, FN and total records for each deployment, validation, and classifier type combinations.-*estscore2* – the scoring of the est using the data driven est z value scoring method.-*est_mean_and_var* – the mean and the variance of each class for each site and deployment combinations. Use to determine the class in NBC.-*probability_of_discrete_data* – the mixed probability distribution for band3, band10, and frequency for each of unique value of pulse. Use to determine the probability in modified BC.-*decision_tree* – the trees for each deployment and site combinations. Use to classify in decision tree method.-*random_forests* – the forests for each deployment and site combinations. Use to classify in random_forests method.
-*SVM_gamma* - the gamma value used to train the final SVM. Use to classify in SVM.
-*SVM_b* - the constant in the hyperplane for SVM. Use to classify in SVM.
-*SVM_alpha* - the nonzero alpha values with the estID its associated with. Use to classify in SVM.

