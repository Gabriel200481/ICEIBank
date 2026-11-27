#!/bin/sh
# Cria, dentro do LocalStack, os recursos "AWS" do ICEIBank.
# Rode UMA vez a cada vez que o LocalStack subir (ele nao guarda estado entre
# reinicios):  docker compose exec localstack sh /scripts/init.sh
set -e
CONTA=000000000000
REGIAO=us-east-1

echo "Criando topico SNS, fila SQS e a inscricao entre eles..."
awslocal sns create-topic --name iceibank-transferencias-concluidas
awslocal sqs create-queue --queue-name comprovantes
awslocal sns subscribe \
  --topic-arn arn:aws:sns:$REGIAO:$CONTA:iceibank-transferencias-concluidas \
  --protocol sqs \
  --notification-endpoint arn:aws:sqs:$REGIAO:$CONTA:comprovantes \
  --attributes RawMessageDelivery=true

echo "Criando bucket S3 e tabela DynamoDB..."
awslocal s3 mb s3://iceibank-comprovantes
awslocal dynamodb create-table \
  --table-name comprovantes \
  --attribute-definitions AttributeName=txId,AttributeType=S \
  --key-schema AttributeName=txId,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

echo "Criando o papel (IAM) e as funcoes Lambda..."
awslocal iam create-role \
  --role-name lambda-role \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
for FUNCAO in gerar-comprovante consultar-comprovante; do
  awslocal lambda create-function \
    --function-name $FUNCAO \
    --runtime python3.12 \
    --handler lambda_function.handler \
    --role arn:aws:iam::$CONTA:role/lambda-role \
    --zip-file fileb:///serverless/$FUNCAO.zip \
    --environment "Variables={BUCKET=iceibank-comprovantes,TABELA=comprovantes}"
done

echo "Ligando a fila SQS a funcao gerar-comprovante..."
awslocal lambda create-event-source-mapping \
  --function-name gerar-comprovante \
  --event-source-arn arn:aws:sqs:$REGIAO:$CONTA:comprovantes \
  --batch-size 5 \
  --function-response-types ReportBatchItemFailures

echo "Expondo consultar-comprovante em um API Gateway: GET /comprovantes/{txId}..."
API=$(awslocal apigateway create-rest-api --name iceibank-comprovantes --query id --output text)
RAIZ=$(awslocal apigateway get-resources --rest-api-id $API --query 'items[0].id' --output text)
RECURSO=$(awslocal apigateway create-resource --rest-api-id $API --parent-id $RAIZ --path-part comprovantes --query id --output text)
PARAMETRO=$(awslocal apigateway create-resource --rest-api-id $API --parent-id $RECURSO --path-part '{txId}' --query id --output text)
awslocal apigateway put-method --rest-api-id $API --resource-id $PARAMETRO --http-method GET --authorization-type NONE
awslocal apigateway put-integration \
  --rest-api-id $API --resource-id $PARAMETRO --http-method GET \
  --type AWS_PROXY --integration-http-method POST \
  --uri arn:aws:apigateway:$REGIAO:lambda:path/2015-03-31/functions/arn:aws:lambda:$REGIAO:$CONTA:function:consultar-comprovante/invocations
awslocal apigateway create-deployment --rest-api-id $API --stage-name local

echo "Pronto. Consulte um comprovante com:"
echo "  http://localhost:4566/restapis/$API/local/_user_request_/comprovantes/<txId>"
