import StringIO
from datetime import datetime, date
from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.contrib.auth import models as auth_models
from filer.models.filemodels import File
from filer.utils.pil_exif import get_exif_for_file, set_exif_subject_location

class Image(File):
    SIDEBAR_IMAGE_WIDTH = 210
    file_type = 'image'
    
    _height = models.IntegerField(null=True, blank=True) 
    _width = models.IntegerField(null=True, blank=True)
    
    date_taken = models.DateTimeField(_('date taken'), null=True, blank=True, editable=False)
    
    default_alt_text = models.CharField(max_length=255, blank=True, null=True)
    default_caption = models.CharField(max_length=255, blank=True, null=True)
    
    author = models.CharField(max_length=255, null=True, blank=True)
    
    must_always_publish_author_credit = models.BooleanField(default=False)
    must_always_publish_copyright = models.BooleanField(default=False)
    
    subject_location = models.CharField(max_length=64, null=True, blank=True, default=None)
    
    def _check_validity(self):
        if not self.name:# or not self.contact:
            return False
        return True
    def sidebar_image_ratio(self):
        if self.width:
            return float(self.width)/float(self.SIDEBAR_IMAGE_WIDTH)
        else:
            return 1.0
    def save(self, *args, **kwargs):
        if self.date_taken is None:
            try:
                exif_date = self.exif.get('DateTimeOriginal',None)
                if exif_date is not None:
                    d, t = str.split(exif_date.values)
                    year, month, day = d.split(':')
                    hour, minute, second = t.split(':')
                    self.date_taken = datetime(int(year), int(month), int(day),
                                               int(hour), int(minute), int(second))
            except:
                pass
        if self.date_taken is None:
            self.date_taken = datetime.now()
        #if not self.contact:
        #    self.contact = self.owner
        self.has_all_mandatory_data = self._check_validity()
        try:
            if self.subject_location:
                parts = self.subject_location.split(',')
                pos_x = int(parts[0])
                pos_y = int(parts[1])
                                                  
                sl = (int(pos_x), int(pos_y) )
                exif_sl = self.exif.get('SubjectLocation', None)
                if self.file and not sl == exif_sl:
                    self.file.open()
                    fd_source = StringIO.StringIO(self.file.read())
                    self.file.close()
                    set_exif_subject_location(sl, fd_source, self.file.path)
        except:
            # probably the image is missing. nevermind
            pass
        try:
            self._width = self.file.width
            self._height = self.file.height
        except:
            # probably the image is missing. nevermind.
            pass
        super(Image, self).save(*args, **kwargs)
        
    def _get_exif(self):
        if hasattr(self, '_exif_cache'):
            return self._exif_cache
        else:
            if self.file:
                self._exif_cache = get_exif_for_file(self.file.path)
            else:
                self._exif_cache = {}
        return self._exif_cache
    exif = property(_get_exif)
    def has_edit_permission(self, request):
        return self.has_generic_permission(request, 'edit')
    def has_read_permission(self, request):
        return self.has_generic_permission(request, 'read')
    def has_add_children_permission(self, request):
        return self.has_generic_permission(request, 'add_children')
    def has_generic_permission(self, request, type):
        """
        Return true if the current user has permission on this
        image. Return the string 'ALL' if the user has all rights.
        """
        user = request.user
        if not user.is_authenticated() or not user.is_staff:
            return False
        elif user.is_superuser:
            return True
        elif user == self.owner:
            return True
        elif self.folder:
            return self.folder.has_generic_permission(request, type)
        else:
            return False
                
    def label(self):
        if self.name in ['',None]:
            return self.original_filename or 'unnamed file'
        else:
            return self.name
    label = property(label)
    @property
    def width(self):
        return self._width_field or 0
    @property
    def height(self):
        return self._height_field or 0
    @property
    def size(self):
        try:
            return self.file.size
        except:
            return 0
    @property
    def thumbnails(self):
        # we build an extra dict here mainly
        # to prevent the default errors to 
        # get thrown and to add a default missing
        # image (not yet)
        if not hasattr(self, '_thumbnails'):
            tns = {}
            for name, tn in self.file.extra_thumbnails.items():
                tns[name] = tn
            self._thumbnails = tns
        return self._thumbnails
    @property
    def url(self):
        '''
        needed to make this behave like a ImageField
        '''
        return self.file.url
    @property
    def absolute_image_url(self):
        return self.url
    @property
    def rel_image_url(self):
        'return the image url relative to MEDIA_URL'
        try:
            rel_url = u"%s" % self.file.url
            if rel_url.startswith('/media/'):
                before, match, rel_url = rel_url.partition('/media/')
            return rel_url
        except Exception, e:
            return ''
    def __unicode__(self):
        # this simulates the way a file field works and
        # allows the sorl thumbnail tag to use the Image model
        # as if it was a image field
        return self.rel_image_url
    class Meta:
        app_label = 'filer'