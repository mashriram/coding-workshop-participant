# Base network structure utilizing the absolutely free $0 AWS Default VPC framework
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# The Security Group binding the Lambda Execution ENI
resource "aws_security_group" "lambda_sg" {
  name        = "coding-workshop-lambda-sg"
  description = "Security group for the cohesive Lambda backend"
  vpc_id      = data.aws_vpc.default.id

  # Egress freely allows Lambda egress across the internal network (to reach RDS)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# The Security Group strictly guarding the Database Instance
resource "aws_security_group" "rds_sg" {
  name        = "coding-workshop-rds-sg"
  description = "Security group for PostgreSQL RDS blocking public access natively"
  vpc_id      = data.aws_vpc.default.id

  # Implicitly trusting only localized internal traffic sourced natively from Lambda
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
