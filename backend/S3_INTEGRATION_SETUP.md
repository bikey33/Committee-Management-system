# AWS S3 Integration - Formation Letter Upload Setup

## ✅ S3 Configuration Complete

Your formation letter upload feature has been successfully integrated with AWS S3 (Garage storage).

### Configuration Summary

#### Backend Changes
1. **Installed Dependencies**
   - `django-storages[s3]==1.14.3` - Django storage backend for S3
   - `boto3==1.34.80` - AWS SDK for Python
   - `python-dotenv==1.2.1` - Environment variable loading

2. **Updated Django Settings** (`cms_backend/settings.py`)
   - Added `storages` app to `INSTALLED_APPS`
   - Configured S3 backend as default file storage
   - Set up all AWS configuration variables from `.env`
   - Conditional S3 backend (falls back to local storage if AWS is not configured)

3. **Updated Committee Serializer** (`committee/serializers.py`)
   - Modified `get_formationLetterURL()` to use `obj.formation_letter.url`
   - This automatically returns S3 URL when using S3 storage backend

#### Environment Configuration (.env)
```
AWS_ACCESS_KEY_ID=GKffa16a401095e4fdd2864c9a
AWS_SECRET_ACCESS_KEY=b2904032d0dc7b93d2c7a6cb02bc713413010578cae60ac6feeb44e55da23b9d
AWS_STORAGE_BUCKET_NAME=committee-storage
AWS_S3_ENDPOINT_URL=https://s3.ntc.net.np
AWS_S3_VERIFY=False
AWS_S3_USE_SSL=True
AWS_S3_REGION_NAME=garage
AWS_S3_ADDRESSING_STYLE=path
AWS_S3_SIGNATURE_VERSION=s3v4
AWS_DEFAULT_ACL=None
AWS_QUERYSTRING_AUTH=False
AWS_S3_FILE_OVERWRITE=False
```

### How It Works

1. **File Upload Flow**
   - Frontend: User uploads formation letter in committee form
   - FormData is sent to Django API with `formation_letter` file
   - Django saves to S3 automatically (using default storage backend)
   - File stored at: `s3://committee-storage/formation_letters/{filename}`

2. **File URL Generation**
   - API returns S3 URL: `https://s3.ntc.net.np/committee-storage/formation_letters/{filename}`
   - Frontend displays link to S3 file
   - Direct access to formation letters via S3

3. **Access Control**
   - AWS credentials used for authentication
   - S3 path-style addressing configured for Garage S3-compatible storage
   - SSL verification disabled for self-signed certificates

### Testing Results

✅ **S3 Connection Test**: PASSED
- Successfully uploaded test file to S3
- Successfully retrieved test file from S3
- Successfully deleted test file from S3
- All S3 operations (PUT, GET, DELETE) working correctly

### File Locations

- **Django Settings**: [cms_backend/settings.py](cms_backend/settings.py#L188-L216)
- **Committee Serializer**: [committee/serializers.py](committee/serializers.py#L105-L109)
- **Requirements**: [requirements.txt](requirements.txt)
- **Environment Config**: [.env](.env#L33-L52)

### What's Next

1. Formation letters uploaded via the committee form will be stored in S3
2. Formation letter URLs will point to S3 bucket directly
3. No local filesystem storage needed for formation letters
4. Files are persisted in the S3/Garage bucket for long-term storage

### Troubleshooting

If you encounter S3 connection issues:

1. Verify `.env` file contains all AWS credentials
2. Check S3 endpoint is accessible: `https://s3.ntc.net.np`
3. Verify bucket exists: `committee-storage`
4. Ensure AWS credentials have permission to read/write to bucket
5. Run test script: `python3 test_s3_upload.py`

### Notes

- Files are uploaded with path prefix: `formation_letters/`
- File overwrite is disabled (`AWS_S3_FILE_OVERWRITE=False`)
- Query string authentication is disabled (files need explicit permissions)
- SSL verification disabled for self-signed certificates on Garage

---

**Status**: ✅ Ready for production use
**Last Updated**: May 13, 2026
**Tested**: Yes - S3 operations confirmed working
