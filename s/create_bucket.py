#!/usr/bin/env python
"""Create the dev media bucket, enable Garage's public website endpoint and
allow cross-origin reads from it.

Run by s/bootstrap inside the web container:

    docker compose run --rm web python s/create_bucket.py

Garage implements neither bucket policies nor ACLs, so public reads are
served anonymously by its website endpoint instead (see garage.toml [s3_web]):
objects are then reachable at http://<bucket>.<AWS_S3_PUBLIC_HOST>/<key>.

The website endpoint honours the bucket's CORS configuration (PutBucketCors),
which the HLS player needs: the site is served from http://localhost:8000
while media is on a different origin, so playlist/segment fetches from the
browser are cross-origin and require Access-Control-Allow-Origin.
"""

import os

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError


def main() -> None:
    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ["AWS_S3_ENDPOINT_URL"],
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4"),
        region_name=os.environ.get("AWS_S3_REGION_NAME", "us-east-1"),
    )
    bucket = os.environ.get("AWS_STORAGE_BUCKET_NAME", "pedtv-media")

    try:
        s3.create_bucket(Bucket=bucket)
        print(f"Bucket '{bucket}' created.")
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            print(f"Bucket '{bucket}' already exists.")
        else:
            raise

    # Enable the website endpoint so objects are served anonymously.
    s3.put_bucket_website(
        Bucket=bucket,
        WebsiteConfiguration={"IndexDocument": {"Suffix": "index.html"}},
    )
    print("Website endpoint enabled (anonymous public reads).")

    # Allow cross-origin reads from the website endpoint. The bucket is
    # public-read anyway, and requests carry no credentials, so any origin
    # is fine for dev.
    s3.put_bucket_cors(
        Bucket=bucket,
        CORSConfiguration={
            "CORSRules": [
                {
                    "AllowedOrigins": ["*"],
                    "AllowedMethods": ["GET", "HEAD"],
                    "AllowedHeaders": ["*"],
                    # Headers the HLS player may read from responses
                    "ExposeHeaders": [
                        "Accept-Ranges",
                        "Content-Length",
                        "Content-Range",
                        "Content-Type",
                        "ETag",
                        "Last-Modified",
                    ],
                }
            ]
        },
    )
    print("CORS enabled (cross-origin GET/HEAD from any origin).")


if __name__ == "__main__":
    main()