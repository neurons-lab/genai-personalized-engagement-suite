"""AWS CDK Deploy Script"""
import os
from constructs import Construct
from aws_cdk import (
    Stack,
    Tags,
    Duration,
    CfnOutput,
    RemovalPolicy,
    aws_elasticloadbalancingv2 as elbv2,
    aws_logs as logs,
    aws_kms as kms,
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_s3 as s3,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_ecr_assets as ecr_assets,
    aws_route53 as route53,
    aws_route53_targets as route53_targets,
    aws_certificatemanager as acm,
)
from cdk_nag import NagSuppressions, NagPackSuppression
from dotenv import load_dotenv
load_dotenv('.env.sample', override=False)
load_dotenv('.env', override=True)


# Stack
class AppStack(Stack):
    """
    Sample Docker App Deployment Stack
    Require:
    - Pre-created HostedZone
    - ZONE_NAME
    - DOMAIN_NAME
    Contians:
    - VPC
    - DockerImage
    - Fargate Cluster
    - Fargate Service App
    """
    def __init__(self, scope: Construct, _id: str, **kwargs) -> None:
        """Init"""
        super().__init__(scope, _id, **kwargs)

        # Env
        zone_name = os.environ.get('ZONE_NAME', 'example.com')
        domain_name = os.environ.get('DOMAIN_NAME', 'app.example.com')
        app_path = os.environ.get('APP_PATH', '../app')
        stack_name = os.getenv('STACK_NAME', 'GenAiPESuiteStack')

        # Cost Center Tag
        Tags.of(self).add('CostCenter', stack_name)

        # Route53 Zone
        hosted_zone = route53.HostedZone.from_lookup(
                self, 'HostedZone', domain_name=zone_name)

        # Cert
        cert = acm.Certificate(
            self, 'AppCert',
            domain_name=domain_name,
            validation=acm.CertificateValidation.from_dns(hosted_zone))

        # VPC
        vpc = ec2.Vpc(
            self, 'AppVpc',
            ip_addresses=ec2.IpAddresses.cidr('10.0.0.0/16'),
            max_azs=2,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name='public',
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                    map_public_ip_on_launch=False
                ),
                ec2.SubnetConfiguration(
                    name='private',
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name='protected',
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24
                )
            ])
        default_security_group = ec2.SecurityGroup.from_security_group_id(
            self, 'default', vpc.vpc_default_security_group
        )

        ec2.CfnSecurityGroupEgress(
            self,
            'AllowOnlyVPCOutbound',
            group_id=default_security_group.security_group_id,
            ip_protocol='-1',
            cidr_ip=vpc.vpc_cidr_block
        )
        ec2.CfnSecurityGroupIngress(
            self,
            'AllowOnlyVPCInbound',
            group_id=default_security_group.security_group_id,
            ip_protocol='-1',
            cidr_ip=vpc.vpc_cidr_block
        )

        # KMS Key for VPC Flow Logs Encryption
        kms_key = kms.Key(
            self, 'VpcFlowLogsKmsKey',
            description='KMS Key for VPC Flow Logs Encryption',
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.DESTROY,
        )
        # KMS Policy to allow VPC Flow Logs to write logs to CloudWatch Logs
        kms_resource_policy_vpc_flow_logs = kms_key.add_to_resource_policy(
            iam.PolicyStatement(
                actions=['kms:Encrypt', 'kms:Decrypt', 'kms:ReEncrypt*', 'kms:GenerateDataKey*', 'kms:DescribeKey'],
                resources=['*'],
                principals=[iam.ServicePrincipal('vpc-flow-logs.amazonaws.com')]
            )
        )
        # KMS Policy to allow CloudWatch Logs to write logs to KMS
        kms_resource_policy_cloudwatch_logs = kms_key.add_to_resource_policy(
            iam.PolicyStatement(
                actions=['kms:Encrypt', 'kms:Decrypt', 'kms:ReEncrypt*', 'kms:GenerateDataKey*', 'kms:DescribeKey'],
                resources=['*'],
                principals=[iam.ServicePrincipal('logs.amazonaws.com')]
            )
        )

        log_group = logs.LogGroup(
            self, 'VpcFlowLogs',
            encryption_key=kms_key,
            removal_policy=RemovalPolicy.DESTROY,
        )

        role = iam.Role(self, 'VpcFlowLogsRole',
            assumed_by=iam.ServicePrincipal('vpc-flow-logs.amazonaws.com')
        )

        ec2.FlowLog(self, 'VpcFlowLog',
            resource_type=ec2.FlowLogResourceType.from_vpc(vpc),
            destination=ec2.FlowLogDestination.to_cloud_watch_logs(log_group, role),
            traffic_type=ec2.FlowLogTrafficType.ALL,
        )
        
        # Docker Image
        image = ecr_assets.DockerImageAsset(
            self, 'AppImage', directory=app_path)

        # Fargate Application
        alb_securiy_group = ec2.SecurityGroup(
            self, 'AppAlbSecurityGroup',
            vpc=vpc,
            allow_all_outbound=True,
            description='App ALB Security Group',
            security_group_name='app-alb-security-group'
        )

        alb_securiy_group.add_ingress_rule(
            description='Allow HTTPS from Internet',
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(443)
        )

        alb_securiy_group.add_ingress_rule(
            description='Allow HTTP from Internet',
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80)
        )

        service_securiy_group = ec2.SecurityGroup(
            self, 'AppServiceSecurityGroup',
            vpc=vpc,
            allow_all_outbound=True,
            description='App Service Security Group',
            security_group_name='app-service-security-group'
        )

        service_securiy_group.add_ingress_rule(
            description='Allow HTTP from ALB',
            peer=alb_securiy_group,
            connection=ec2.Port.tcp(80)
        )

        service_securiy_group.add_ingress_rule(
            description='Allow HTTPS from ALB',
            peer=alb_securiy_group,
            connection=ec2.Port.tcp(443)
        )

        alb = elbv2.ApplicationLoadBalancer(
            self, 'AppAlb',
            vpc=vpc,
            internet_facing=True,
            security_group=alb_securiy_group,
            drop_invalid_header_fields=True,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            deletion_protection=True,
        )
        # ALB log bucket
        alb_log_bucket = s3.Bucket(
            self, 'AppAlbLogBucket',
            enforce_ssl=True,
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
            ## ELB does not support KMS CMK keys for access logs currently
            # encryption=s3.BucketEncryption.KMS,
            # encryption_key=kms_key,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )

        # enable ALB logs
        alb.log_access_logs(
            bucket=alb_log_bucket,
            prefix='app-alb'
        )

        # ECS Cluster
        cluster = ecs.Cluster(
            self, 'AppCluster',
            vpc=vpc,
            container_insights=True,
        )

        # ECS Task Definition Role to access SSM Parameter Store
        task_definition_role = iam.Role(
            self, 'AppTaskDefinitionRole',
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
                iam.ServicePrincipal('ecs.amazonaws.com'),
                # iam.ServicePrincipal('ec2.amazonaws.com'),
            ),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AmazonECSTaskExecutionRolePolicy'),
                iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSSMReadOnlyAccess'),
            ],
            inline_policies={
                'LogBucketAccessPolicy': iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                's3:PutObject',
                                's3:GetObject',
                                's3:ListBucket',
                                's3:DeleteObject',
                            ],
                            resources=[
                                alb_log_bucket.bucket_arn,
                                alb_log_bucket.bucket_arn + '/*',
                            ],
                        ),
                    ],
                ),
                'BedrockAccessPolicy': iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=['bedrock:*'],
                            resources=['*'],
                        ),
                    ],
                ),
            },
        )

        # ECS Task Definition
        task_definition = ecs.FargateTaskDefinition(
            self, 'AppTaskDefinition',
            cpu=256,
            memory_limit_mib=512,
            execution_role=task_definition_role,
            task_role=task_definition_role,
        )

        # ECS Log Group
        task_log_group = logs.LogGroup(
            self, 'AppTaskLogs',
            encryption_key=kms_key,
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # ECS Task Definition Container
        container = task_definition.add_container(
            'AppContainer',
            image=ecs.ContainerImage.from_docker_image_asset(image),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix='app',
                log_group=task_log_group,
            ),
            port_mappings=[
                ecs.PortMapping(
                    container_port=80,
                    host_port=80,
                    protocol=ecs.Protocol.TCP
                ),
                ecs.PortMapping(
                    container_port=443,
                    host_port=443,
                    protocol=ecs.Protocol.TCP
                )
            ]
        )

        service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, 'AppService',
            cluster=cluster,
            desired_count=1,
            public_load_balancer=True,
            certificate=cert,
            task_definition=task_definition,
            task_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[service_securiy_group],
            load_balancer=alb,
        )
        CfnOutput(
            self, 'AppServiceAlbUrl{}'.format(stack_name), description='App Service ALB URL',
            export_name='appServiceAlbUrl{}'.format(stack_name), value=service.load_balancer.load_balancer_dns_name)

        # Domain
        domain = route53.ARecord(
            self, 'AppDomain',
            zone=hosted_zone,
            record_name=domain_name,
            target=route53.RecordTarget.from_alias(
                route53_targets.LoadBalancerTarget(service.load_balancer)),
            ttl=Duration.seconds(60))
        CfnOutput(
            self, 'AppServiceUrl{}'.format(stack_name), description='App Service URL',
            export_name='appServiceUrl{}'.format(stack_name), value='https://{}'.format(domain.domain_name))

        # NAG

        # AwsSolutions-IAM4
        for resource_path in [
            '/GenAiPESuiteStack/AppTaskDefinitionRole/Resource',
        ]:
            NagSuppressions.add_resource_suppressions_by_path(
                self, resource_path,
                [NagPackSuppression(id='AwsSolutions-IAM4', reason='Managed policy used')])
        
        # AwsSolutions-IAM5
        for resource_path in [
            '/GenAiPESuiteStack/AppTaskDefinitionRole/DefaultPolicy/Resource',
        ]:
            NagSuppressions.add_resource_suppressions_by_path(
                self, resource_path,
                [NagPackSuppression(id='AwsSolutions-IAM5', reason='Wildcard in autogenerated resource')])
        
        # HIPAA.Security-IAMNoInlinePolicy
        for resource_path in [
            '/GenAiPESuiteStack/AppTaskDefinitionRole/DefaultPolicy/Resource',
            '/GenAiPESuiteStack/VpcFlowLogsRole/DefaultPolicy/Resource',
        ]:
            NagSuppressions.add_resource_suppressions_by_path(
                self, resource_path,
                [NagPackSuppression(id='HIPAA.Security-IAMNoInlinePolicy', reason='Cdk inline policy')])

        # HIPAA.Security-VPCNoUnrestrictedRouteToIGW
        for resource_path in [
            '/GenAiPESuiteStack/AppVpc/publicSubnet1/DefaultRoute',
            '/GenAiPESuiteStack/AppVpc/publicSubnet2/DefaultRoute',
        ]:
            NagSuppressions.add_resource_suppressions_by_path(
                self, resource_path,
                [NagPackSuppression(id='HIPAA.Security-VPCNoUnrestrictedRouteToIGW', reason='Public subnet')])

        # AwsSolutions-EC23
        for resource_path in [
            '/GenAiPESuiteStack/AppAlbSecurityGroup/Resource',
        ]:
            NagSuppressions.add_resource_suppressions_by_path(
                self, resource_path,
                [NagPackSuppression(id='AwsSolutions-EC23', reason='This ALB are public accessed')])

        # S3 Bucket Rules
        NagSuppressions.add_resource_suppressions_by_path(
            self, '/GenAiPESuiteStack/AppAlbLogBucket/Resource',
            [
                NagPackSuppression(id='AwsSolutions-S1', reason='No need for logging access to log bucket'),
                NagPackSuppression(id='HIPAA.Security-S3BucketLoggingEnabled', reason='No need for logging access to log bucket'),
                NagPackSuppression(id='HIPAA.Security-S3BucketReplicationEnabled', reason='No need for replication of log bucket'),
            ])
    