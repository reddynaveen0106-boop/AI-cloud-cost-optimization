pipeline {
    agent any

    stages {

        stage('Install Dependencies') {
            steps {
                sh '''
                    python3 --version
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Python Validation') {
            steps {
                sh '''
                    . venv/bin/activate
                    python -m compileall backend
                '''
            }
        }

        stage('Docker Build') {
            steps {
                sh '''
                    docker build -t ai-cost-optimization .
                '''
            }
        }
    }
}