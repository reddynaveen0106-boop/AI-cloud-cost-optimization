pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Test Connection') {
            steps {
                sh 'echo "Jenkins successfully triggered!"'
                sh 'git log -1 --oneline'
            }
        }
    }
}