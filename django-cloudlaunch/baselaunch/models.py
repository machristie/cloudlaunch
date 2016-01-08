from django.contrib.auth.models import User
from django.db import models
from django.template.defaultfilters import slugify


class DateNameAwareModel(models.Model):
    # Automatically add timestamps when object is created
    added = models.DateTimeField(auto_now_add=True)
    # Automatically add timestamps when object is updated
    updated = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=60)

    class Meta:
        abstract = True

    def __str__(self):
        return "{0}".format(self.name)


class Cloud(DateNameAwareModel):
    # Ideally, this would be a proxy class so it can be used to uniformly
    # retrieve all cloud objects (e.g., Cloud.objects.all()) but without
    # explicitly existing in the database. However, without a parent class
    # (e.g., Infrastructure), this cannot be due to Django restrictions
    # https://docs.djangoproject.com/en/1.9/topics/db/
    #   models/#base-class-restrictions
    kind = models.CharField(max_length=10, default='cloud', editable=False)
    slug = models.SlugField(max_length=50, primary_key=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            # Newly created object, so set slug
            self.slug = slugify(self.name)
        super(Cloud, self).save(*args, **kwargs)


class AWS(Cloud):
    compute = models.ForeignKey('EC2', blank=True, null=True)
    object_store = models.ForeignKey('S3', blank=True, null=True)

    class Meta:
        verbose_name = "AWS"
        verbose_name_plural = "AWS"


class EC2(DateNameAwareModel):
    ec2_region_name = models.CharField(max_length=100,
                                       verbose_name="EC2 region name")
    ec2_region_endpoint = models.CharField(
        max_length=255, verbose_name="EC2 region endpoint")
    ec2_conn_path = models.CharField(max_length=255, default='/',
                                     verbose_name="EC2 conn path")
    ec2_is_secure = models.BooleanField(default=True,
                                        verbose_name="EC2 is secure")
    ec2_port = models.IntegerField(blank=True, null=True,
                                   verbose_name="EC2 port")

    class Meta:
        verbose_name = "EC2"
        verbose_name_plural = "EC2"


class S3(DateNameAwareModel):
    s3_host = models.CharField(max_length=255, blank=True, null=True)
    s3_conn_path = models.CharField(max_length=255, default='/', blank=True,
                                    null=True)
    s3_is_secure = models.BooleanField(default=True)
    s3_port = models.IntegerField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "S3"


class OpenStack(Cloud):
    auth_url = models.CharField(max_length=255)
    region_name = models.CharField(max_length=100)

    class Meta:
        verbose_name = "OpenStack"
        verbose_name_plural = "OpenStack"


class Image(DateNameAwareModel):
    """
    A base Image model used by a virtual appliance.

    Applications will use Images and the same application may be available
    on multiple infrastructures so we need this base class so a single
    application field can be used to retrieve all images across
    infrastructures.
    """
    image_id = models.CharField(max_length=50, verbose_name="Image ID")
    description = models.CharField(max_length=255, blank=True, null=True)


class CloudImage(Image):
    cloud = models.ForeignKey(Cloud, blank=True, null=True)

    def __str__(self):
        return "{0} (on {1})".format(self.name, self.cloud.name)


class Application(DateNameAwareModel):
    slug = models.SlugField(max_length=50, primary_key=True)
    description = models.TextField(blank=True, null=True)
    info_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return "{0}".format(self.name)

    def save(self, *args, **kwargs):
        if not self.slug:
            # Newly created object, so set slug
            self.slug = slugify(self.name)
        super(Application, self).save(*args, **kwargs)


class ApplicationVersion(models.Model):
    application = models.ForeignKey(Application, related_name="versions")
    version = models.CharField(max_length=30)
    # Image provides a link to the infrastructure and is hence a ManyToMany
    # field as the same application definition and version may be available
    # on multiple infrastructures.
    images = models.ManyToManyField(Image, blank=True,
                                    related_name="applications")
    # Userdata max length is 16KB
    launch_data = models.TextField(max_length=1024 * 16, help_text="Instance "
                                   "user data to parameterize the launch.",
                                   blank=True, null=True)


class AWSCredentials(DateNameAwareModel):
    cloud = models.ManyToManyField(AWS)
    access_key = models.CharField(max_length=50)
    secret_key = models.CharField(max_length=50, blank=True, null=True)
    user_profile = models.ForeignKey('UserProfile')

    class Meta:
        verbose_name = "AWS Credentials"
        verbose_name_plural = "AWS Credentials"


class OpenStackCredentials(DateNameAwareModel):
    cloud = models.ManyToManyField(OpenStack)
    username = models.CharField(max_length=50)
    password = models.CharField(max_length=50, blank=True, null=True)
    tenant_name = models.CharField(max_length=50)
    user_profile = models.ForeignKey('UserProfile')

    class Meta:
        verbose_name = "OpenStack Credentials"
        verbose_name_plural = "OpenStack Credentials"


class UserProfile(models.Model):
    # Link UserProfile to a User model instance
    user = models.OneToOneField(User)
    slug = models.SlugField(unique=True, primary_key=True, editable=False)

    def __str__(self):
        return "{0} ({1} {2})".format(self.user.username, self.user.first_name,
                                      self.user.last_name)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.user.username)
        super(UserProfile, self).save(*args, **kwargs)
