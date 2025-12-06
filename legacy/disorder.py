import os
import pandas as pd
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split


class Disorder():
    '''
    Represents the disorder of a person.
    Based on their input from a form, it will
    diagnose them through a machine learning algorithm.
    '''

    def __init__(self):
        pass

    def _survey(self, features):
        """
        You guys do NOT need this function. I am just using it for testing. 
        """
        
        response = []
        for column in features.columns:
            response.append(input(f"Does the person have {column}? Enter yes or no: "))
            
        
        
        return response



    def diagnosis(self, model, response, features):
        """
        Description:
        This function deploys our model to find the disorder a user has
        Parameters:
        Takes a model and a dataframe of symptoms
        Return:
        None 
        """

        # Initialize an empty DataFrame
        symptoms = pd.DataFrame(columns=features.columns)

        index = 0
        for column in features.columns:
            symptoms.loc[0, column] = 'no'
            symptoms.loc[1, column] = 'yes'
            # Store the response in the dataframe
            symptoms.loc[2, column] = response[index]
            index += 1
            
        symptoms = pd.get_dummies(symptoms)
        symptoms.drop([0, 1], inplace=True)
        
        disorder = model.predict(symptoms)
        
        return(disorder)

    def _test_accuracy(self, labels, features, model):
        """
        Description:
        This function is for testing the accuracy of our model.
        We do this on both the training score and the testing score.
        
        Parameters:
        labels (disorders), features (symptoms), model 
        Return:
        None
        """

        features_train, features_test, labels_train, labels_test = \
        train_test_split(features, labels, test_size=0.25)
        
        # Compute training accuracy
        train_predictions = model.predict(features_train)
        print('Train Accuracy:', accuracy_score(labels_train, train_predictions))

        # Compute test accuracy
        test_predictions = model.predict(features_test)
        print('Test  Accuracy:', accuracy_score(labels_test, test_predictions))

    def train_model(self, df):
        """
        Description:
        This function separates the data into features and labels. 
        The first step is to get One Hot Encoding of the features.
        Next we create an untrained model with a hyperparameter.
        Then we train our data on the features and labels.
        Parameters:
        The full dataset in a dataframe df
        Return:
        The trained model
        """
        
        features = df.loc[:, df.columns != 'Disorder']
        # one hot encoding
        features = pd.get_dummies(features)
        labels = df['Disorder']

        # Create an untrained model
        model = DecisionTreeClassifier(max_depth=3)
        
        # Train it on our training data
        model.fit(features, labels)

        self._test_accuracy(labels, features, model)
        
        return model

            
    def getDisorder(self, symptoms):
        print(symptoms)
        #print(os.getcwd()) #/TSA-Software-Development
        df = pd.read_csv('Static/Data/dataset.csv')
        model = self.train_model(df)


        # Get user input for symptoms (use your own user input)
        ## symptoms = self._survey(df.drop(columns=['Disorder']))
        
        
        # make sure the symptoms you guys get are in the same order I sent you
        return (self.diagnosis(model, symptoms, df.drop(columns=['Disorder'])))

