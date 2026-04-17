resource "random_password" "postgres_password" {
  length           = 16
  special          = true
  override_special = "!#%*+,-.:?^_{|}~"
}

resource "aws_db_subnet_group" "default" {
  name       = "coding-workshop-db-subnet-group"
  subnet_ids = data.aws_subnets.default.ids
}

resource "aws_db_instance" "postgres" {
  identifier           = "coding-workshop-postgres"
  engine               = "postgres"
  engine_version       = "16" # Aligning perfectly with local docker PG 16 bounds
  instance_class       = "db.t3.micro" # Free tier capable lightweight instance perfectly sized for the workshop payload
  allocated_storage    = 20
  storage_type         = "gp2"
  
  db_name              = "acme_db"
  username             = "postgres"
  password             = random_password.postgres_password.result
  
  db_subnet_group_name   = aws_db_subnet_group.default.name
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  
  # Lock it firmly inside the VPC for structural integrity
  publicly_accessible  = false
  skip_final_snapshot  = true
}
