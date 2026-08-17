pipeline {
    agent any

    stages {
        stage('Test Connection') {
            steps {
                sh 'echo "Jenkins successfully triggered!"'
                sh 'git log -1 --oneline'
            }
        }
    }
}