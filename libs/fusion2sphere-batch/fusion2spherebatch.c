#include "fusion2spherebatch.h"
#include <dirent.h>

FISHEYE fisheye[2];           // Input fisheye
PARAMS params;                // General parameters

// These are known frame templates
// The appropriate one to use will be auto detected, error is none match
#define NTEMPLATE 2

FRAMESPECS template[NTEMPLATE] = {{3104,3000,0,0,0,0},{2704,2624,0,0,0,0},{1568,1504,0,0,0,0}};
int whichtemplate = -1;  

typedef struct {
   char name[256];
	char nprefix[256];
	char prefix[3];
    char extension[4];
    int status;
} FUSIONIMAGE;

typedef struct {
	FUSIONIMAGE front;
	FUSIONIMAGE back;
} FUSIONIMAGES;

// Lookup table
typedef struct {
   UV uv;
} LLTABLE;
LLTABLE *lltable = NULL;
int ntable = 0;
int itable = 0;

int readJPGFast(FISHEYE *fJPG)
{
	FILE *fimg;
	int w,h,d;
	if ((fimg = fopen(fJPG->fname,"rb")) == NULL) {
		fprintf(stderr,"   Failed to open image file \"%s\"\n",fJPG->fname);
		return(FALSE);
	}
	//JPEG_Info(fimg, &fJPG->width, &fJPG->height,&d);
	if (JPEG_Read(fimg, fJPG->image,&fJPG->width,&fJPG->height) != 0) {
		fprintf(stderr,"   Failed to correctly read image \"%s\"\n",fJPG->fname);
		return(FALSE);
	}
	return(TRUE);
}

int readJPG(FISHEYE *fJPG)
{
	FILE *fimg;
	int w,h,d;
	if ((fimg = fopen(fJPG->fname,"rb")) == NULL) {
		fprintf(stderr,"   Failed to open image file \"%s\"\n",fJPG->fname);
		return(FALSE);
	}
	JPEG_Info(fimg, &fJPG->width, &fJPG->height,&d);
	
	fJPG->image = Create_Bitmap(fJPG->width, fJPG->height);
	if (JPEG_Read(fimg, fJPG->image,&w,&h) != 0) {
		fprintf(stderr,"   Failed to correctly read image \"%s\"\n",fJPG->fname);
		return(FALSE);
	}
	return(TRUE);
}

int GetNamePrefixed(char *name, FUSIONIMAGE *image){
    int j = 0;
    int k =0;
    int len = strlen(name); 
    char prefix[3] = {'\0'};
    char extension[4] = {'\0'};
    char nprefix[256] = {'\0'};
    int vtype = 0;
    if(len > 7){
        for(int i=0;i<len;i++){
            if((i < 2) && (i >= 0)){
                prefix[i] = name[i];
            }
            else if(i >= (len-4)){
                extension[k] = name[i];
                k++;
            }
            else{
                nprefix[j] = name[i];
                j++;
            }
        }
        if((strcmp(prefix, "GF") == 0)){
            vtype = 1;//front image prefix
        }
        else if((strcmp(prefix, "GB") == 0)){
            vtype = 2;//back image prefix
        }
        if((vtype == 1) || (vtype == 2)){
            strcpy(image->name, name);
            strcpy(image->prefix, prefix);
            strcpy(image->nprefix, nprefix);
            strcpy(image->extension, extension);
        }
    }
    if(vtype == 0){
        printf("\nPlease make sure images are fusion images.\n");
        exit(-1);
    }
    return vtype;
}

int ReadFusionDirectory(char *dirname, FUSIONIMAGES *fimages, int *icount){
    FUSIONIMAGE f_front;
    FUSIONIMAGE f_back;
    DIR *dir;
    struct dirent *ent;
    int i = 0;
    int j = 0;
    int count=0;
    int vtype = 0;
    char images[2000][256] = { '\0' };
    char s[256] = {'\0'};
    if ((dir = opendir (dirname)) != NULL) {
        /* print all the files and directories within directory */
        while ((ent = readdir (dir)) != NULL) {
            if(ent->d_type == 8){
               if(count > 2000){
                  printf("Max image count is 2000.");
                  break;
               }
                strcpy(images[i],ent->d_name);
                //printf("\n%s %d\n", images[i], ent->d_type);
                i++;
                count++;
            }  
        }
        closedir (dir);
    } 
    else {
        /* could not open directory */
        printf("\nCould not open directory\n");
        exit(-1);
    }
    i = 0;
    const int TOTAL_IMAGE_COUNT = count;
    for( i=0;i<TOTAL_IMAGE_COUNT;i++){
        for( j=i+1;j<TOTAL_IMAGE_COUNT;j++){
            if(strcmp(images[i],images[j])>0){
                strcpy(s,images[i]);
                strcpy(images[i],images[j]);
                strcpy(images[j],s);
            }
        }
    }
    int found = 0;
    int vfront = 0;
    int vback = 0;
    for(int counter = 0; counter<TOTAL_IMAGE_COUNT; counter++){
        if(strlen(images[counter]) > 7){
            vback = 0;
            vback = GetNamePrefixed(images[counter], &f_back);
            found = 0;
            if((strcmp(f_back.prefix, "GB") == 0) && (vback == 2)){
                for(int zcounter = 0; zcounter<TOTAL_IMAGE_COUNT; zcounter++){
                    if((strlen(images[zcounter]) > 7) && (strcmp(images[counter], images[zcounter]) != 0)){
                        vfront = 0;
                        vfront = GetNamePrefixed(images[zcounter], &f_front);
                        if((strcmp(f_front.nprefix, f_back.nprefix) == 0) && (vfront == 1)){
                            strcpy(fimages[counter].front.prefix, f_front.prefix);
                            strcpy(fimages[counter].front.nprefix, f_front.nprefix);
                            strcpy(fimages[counter].front.name, f_front.name);
                            strcpy(fimages[counter].back.prefix, f_back.prefix);
                            strcpy(fimages[counter].back.nprefix, f_back.nprefix);
                            strcpy(fimages[counter].back.name, f_back.name);
                            found = 1;
                            (*icount)++;
                            //printf("\n%s \n", fimages[counter].front.nprefix);
                            break;
                        }
                    }
                }
               if(found != 1){
                  printf("\nOnly jpg images with prefixes GB and GF are allowed. Note, the files must retain the same name as generated on the camera.\n");
                  exit(-1);
               }
            }

        }
    }
    return 0;
}

/*
	Given a longitude and latitude calculate the rgb value from the fisheye
	Return FALSE if the pixel is outside the fisheye image
*/
int FindFishPixel(int n,double latitude,double longitude,UV *uv, int width, int height)
{
	char ind[256];
	int k,index;
	COLOUR c;
	HSV hsv;
	XYZ p,q = {0,0,0};
	double theta,phi,r;
	int u,v;
	double ln = longitude;
	UV fuv;

   // Ignore pixels that will never be touched because out of blend range
   if (n == 0) {
      if (longitude > params.blendmid + params.blendwidth || longitude < -params.blendmid - params.blendwidth)
			return(FALSE);
	}
   if (n == 1) {
      if (longitude > -params.blendmid + params.blendwidth && longitude < params.blendmid - params.blendwidth)
			return(FALSE); 
   }

	// Turn by 180 degrees for the second fisheye
	if (n == 1) {
		longitude += M_PI;
		//printf("\nturn 180 deg %lf\n", longitude);
	}

   // p is the ray from the camera position into the scene
   p.x = cos(latitude) * sin(longitude);
   p.y = cos(latitude) * cos(longitude);
   p.z = sin(latitude);

   

   // Apply fisheye correction transformation
   for (k=0;k<fisheye[n].ntransform;k++) {
	   printf("Apply fisheye correction transformation");
      switch(fisheye[n].transform[k].axis) {
      case XTILT:
		   q.x =  p.x;
   		q.y =  p.y * fisheye[n].transform[k].cvalue + p.z * fisheye[n].transform[k].svalue;
   		q.z = -p.y * fisheye[n].transform[k].svalue + p.z * fisheye[n].transform[k].cvalue;
         break;
      case YROLL:
		   q.x =  p.x * fisheye[n].transform[k].cvalue + p.z * fisheye[n].transform[k].svalue;
		   q.y =  p.y;
		   q.z = -p.x * fisheye[n].transform[k].svalue + p.z * fisheye[n].transform[k].cvalue;
         break;
      case ZPAN:
		   q.x =  p.x * fisheye[n].transform[k].cvalue + p.y * fisheye[n].transform[k].svalue;
		   q.y = -p.x * fisheye[n].transform[k].svalue + p.y * fisheye[n].transform[k].cvalue;
		   q.z =  p.z;
         break;
      }
		p = q;
   }

   // Calculate fisheye coordinates
   theta = atan2(p.z,p.x);
   phi = atan2(sqrt(p.x*p.x+p.z*p.z),p.y);
   r = phi / fisheye[n].fov; // 0 ... 1

   // Determine the u,v coordinate
   u = fisheye[n].centerx + fisheye[n].radius * r * cos(theta);
   //printf("u: %d, fisheye[n].width: %d", u, fisheye[n].width);
   if (u < 0 || u >= width)
      return(FALSE);

   v = fisheye[n].centery + fisheye[n].radius * r * sin(theta);

   if (v < 0 || v >= height)
       return(FALSE);
	index = v * width + u;
	
	sprintf(ind,"%d%d",index, n);
	fuv.index = atoi(ind);

	*uv = fuv;

	return(TRUE);
}

int main(int argc,char **argv)
{
	int i,j,aj,ai,n=0;
	int index,nantialias[2],inblendzone;
	char basename[256],outfilename[256] = "\0",frontinfilename[256] = "\0",backinfilename[256] = "\0";
	BITMAP4 black = {0,0,0,255},red = {255,0,0,255};
	double latitude0,longitude0,latitude,longitude;
	double weight = 1,blend = 1;
	COLOUR rgb,rgbsum[2],rgbzero = {0,0,0};
	double starttime,stoptime=0;
	int nopt,noptiterations = 1; // > 1 for optimisation
	double fov[2];
	int centerx[2],centery[2];
	double r,theta,minerror=1e32,opterror=0,errorsum = 0;
	int nsave = 0;
	char fname[256];
	int nfish = 0;
	FILE *fptr;

	FUSIONIMAGES fimages[2000];
	char actualpath [PATH_MAX];
	char *sptr;
	int img_count = 0;
	char *full_front;
	char *full_back;
	int sdir = 0;

	char fnameout[256],fname1[256],fname2[256],tablename[256];
	int face,nframe, mcount = 0, nt=0, nstart=0, nstop=0, nn = 0;
	int width = 0, height = 0;
	double dx,dy;
	UV uv;
   // Memory for images, 2 input frames and one output equirectangular
   BITMAP4 *spherical = NULL;


	// Initial values for fisheye structure and general parameters
	InitParams();
	InitFisheye(&fisheye[0]);
	InitFisheye(&fisheye[1]);

	// Create basename
	strcpy(basename,argv[argc-1]);
	for (i=0;i<strlen(basename);i++)
		if (basename[i] == '.')
			basename[i] = '\0';

	// Parse the command line arguments 
	for (i=1;i<argc;i++) {
		if (strcmp(argv[i],"-w") == 0) {
			i++;
			params.outwidth = atoi(argv[i]);
			params.outwidth /= 4; 
			params.outwidth *= 4; // Ensure multiple of 4
			params.outheight = params.outwidth / 2;     // Default for equirectangular images, will be even
		} else if (strcmp(argv[i],"-a") == 0) {
			i++;
			if ((params.antialias = atoi(argv[i])) < 1)
				params.antialias = 1;
		} else if (strcmp(argv[i],"-b") == 0) {
        	i++;
        	if ((params.blendwidth = DTOR*atof(argv[i])) < 0)
				params.blendwidth = 0;
			params.blendwidth /= 2; // Now half blendwith
		} else if (strcmp(argv[i],"-d") == 0) {
			params.debug = TRUE;
		} else if (strcmp(argv[i],"-q") == 0) {
			i++;
         params.blendpower = atof(argv[i]);
		} else if (strcmp(argv[i],"-o") == 0) { // ./%06d.jpg  
			i++;
			strcpy(outfilename,argv[i]);
		} else if (strcmp(argv[i],"-x") == 0) { 
			i++;
			strcpy(frontinfilename,argv[i]); // ./front/%06d.jpg
			i++;
			strcpy(backinfilename,argv[i]); // ./back/%06d.jpg
		} 
		else if (strcmp(argv[i],"-e") == 0) {
         i++;
         noptiterations = atoi(argv[i]);
		} else if (strcmp(argv[i],"-p") == 0) {
         i++;
         params.deltafov = DTOR*atof(argv[i]);
         i++;
         params.deltacenter = atoi(argv[i]);
         i++;
         params.deltatheta = DTOR*atof(argv[i]);
      } else if (strcmp(argv[i],"-i") == 0) {
         params.icorrection = TRUE;
      } else if (strcmp(argv[i],"-m") == 0) {
			i++;
         params.blendmid = atof(argv[i]);
			params.blendmid *= (DTOR*0.5);
	  } else if (strcmp(argv[i],"-g") == 0) {
		  i++;
         nstart = atoi(argv[i]);
      } else if (strcmp(argv[i],"-h") == 0) {
		  i++;
         nstop = atoi(argv[i]);
	  }
	}


	if (strlen(outfilename) > 2) {
		if (!CheckTemplate(outfilename,1))     // Delete user selected output filename template
			outfilename[0] = '\0';
		if (!CheckTemplate(frontinfilename,1))     // Delete user selected output filename template
			frontinfilename[0] = '\0';
		if (!CheckTemplate(backinfilename,1))     // Delete user selected output filename template
			backinfilename[0] = '\0';
	}
	else{
		exit(-1);
	}




   // Check the first frame to determine template and frame sizes
	sprintf(fname1,frontinfilename,nstart);
	sprintf(fname2,backinfilename,nstart);

	//printf("\n %s %s\n", fname1, fname2);

	if ((whichtemplate = CheckFrames(fname1,fname2,&width,&height)) < 0)
		exit(-1);
   if (params.debug) {
      fprintf(stderr,"%s() - frame dimensions: %d x %d\n",argv[0],width,height);
		fprintf(stderr,"%s() - Expect frame template %d\n",argv[0],whichtemplate+1);
	}

	//printf("\nfname1: %s fname2: %s, whichtemplate: %d, width: %d, height: %d\n", fname1, fname2, whichtemplate, width, height);
	//exit(0);

	fisheye[0].width = width;
	fisheye[0].height = height;
	fisheye[1].width = width;
	fisheye[1].height = height;

	//printf("\n width: %d, height: %d\n", width, height);

   // Memory for images
   fisheye[0].image = Create_Bitmap(width,height);
   fisheye[1].image = Create_Bitmap(width,height);

   // Create output spherical (equirectangular) image
   spherical = Create_Bitmap(params.outwidth,params.outheight);

   // Read parameter file name
   if (!ReadParameters(argv[argc-1])) {
      fprintf(stderr,"Failed to read parameter file \"%s\"\n",argv[argc-1]);
      exit(-1);
   }

	// Apply defaults and precompute values
	FisheyeDefaults(&fisheye[0]);
	FisheyeDefaults(&fisheye[1]);
	FlipFisheye(fisheye[0]);
	FlipFisheye(fisheye[1]);


	ntable = params.outheight * params.outwidth * params.antialias * params.antialias * 2;
	lltable = malloc(ntable*sizeof(LLTABLE));
	sprintf(tablename,"f_%d_%d_%d_%d.data",whichtemplate,params.outwidth,params.outheight,params.antialias);

	if ((fptr = fopen(tablename,"r")) != NULL) {
		if (params.debug)
			fprintf(stderr,"%s() - Reading lookup table\n",argv[0]);
		if ((nt = fread(lltable,sizeof(LLTABLE),ntable,fptr)) != ntable) {
			fprintf(stderr,"%s() - Failed to read lookup table \"%s\" (%d != %d)\n",argv[0],tablename,nt,ntable);
		}
		fclose(fptr);
	}

	dx = params.antialias * params.outwidth;
	dy = params.antialias * params.outheight;

	if (nt != ntable) {
		itable = 0;
		mcount = 0;

		for (j=0;j<params.outheight;j++) {
			latitude0 = PI * j / (double)params.outheight - PID2; // -pi/2 ... pi/2
			for (i=0;i<params.outwidth;i++) {
				longitude0 = TWOPI * i / (double)params.outwidth - PI; // -pi ... pi
				for (ai=0;ai<params.antialias;ai++) {
					longitude = longitude0 + ai * TWOPI / dx;
					for (aj=0;aj<params.antialias;aj++) {
						latitude = latitude0 + aj * M_PI / dy;
						for (n=0;n<2;n++) {
							if(FindFishPixel(n,latitude,longitude,&(lltable[itable].uv), width, height)) {
								itable++;
							}
						}
					} // aj
				} // ai
				lltable[itable].uv.index = -1;
				itable++;
			} // i
		} // j

		fptr = fopen(tablename,"w");
		fwrite(lltable,ntable,sizeof(LLTABLE),fptr);
		fclose(fptr);

	}

	for (nframe=nstart;nframe<=nstop;nframe++) {

		sprintf(fisheye[0].fname,frontinfilename,nframe);
		sprintf(fisheye[1].fname,backinfilename,nframe);

		sprintf(fnameout,outfilename,nframe);

		if (IsJPEG(fisheye[0].fname)){
			if(1 != readJPGFast(&fisheye[0])){
				continue;
			}
		}
		if (IsJPEG(fisheye[1].fname)){
			if(1 != readJPGFast(&fisheye[1])){
				continue;
			}
		}
		
		itable = 0;
		Erase_Bitmap(spherical,params.outwidth,params.outheight,black);

		for (j=0;j<params.outheight;j++) {
			latitude0 = PI * j / (double)params.outheight - PID2; // -pi/2 ... pi/2
			for (i=0;i<params.outwidth;i++) {
				longitude0 = TWOPI * i / (double)params.outwidth - PI; // -pi ... pi

				// Blending masks, only depend on longitude
				if (params.blendwidth > 0) {
					blend = (params.blendmid + params.blendwidth - fabs(longitude0)) / (2*params.blendwidth); // 0 ... 1
					if (blend < 0) blend = 0;
					if (blend > 1) blend = 1;
					if (params.blendpower > 1) {
							blend = 2 * blend - 1; // -1 to 1
						blend = 0.5 + 0.5 * SIGN(blend) * pow(fabs(blend),1.0/params.blendpower);
						}
				} else { // No blend
					blend = 0;
					if (ABS(longitude0) <= params.blendmid) // Hard edge
						blend = 1;
				}
		
				// Are we in the blending zones
				inblendzone = FALSE;
				if (longitude0 <= params.blendmid + params.blendwidth && longitude0 >= params.blendmid - params.blendwidth)
					inblendzone = TRUE;
				if (longitude0 >= -params.blendmid - params.blendwidth && longitude0 <= -params.blendmid + params.blendwidth)
					inblendzone = TRUE;


				//printf("\n %lf, %lf, %lf\n", params.blendwidth, params.blendmid, params.blendpower);// 0.000000, 1.570796, 1.000000

				// Initialise antialiasing accumulation variables
				for (n=0;n<2;n++) {
					rgbsum[n] = rgbzero;
					nantialias[n] = 0;
				}

				for (n=0;n<100;n++) {
					nn = 0;
					index = lltable[itable].uv.index;
					if(index == -1){
						itable++;
						break;
					}
					nn = index%10;
					index = index/10;
					//if(nn == 0){printf("\nnn: %d, index: %d, itable: %d\n", nn, index, itable);}
					
					rgbsum[nn].r += fisheye[nn].image[index].r;
					rgbsum[nn].g += fisheye[nn].image[index].g;
					rgbsum[nn].b += fisheye[nn].image[index].b;
					nantialias[nn]++;

					itable++;
				}


				// Normalise by antialiasing samples
				for (n=0;n<2;n++) {
					if (nantialias[n] > 0) {
						rgbsum[n].r /= nantialias[n];
						rgbsum[n].g /= nantialias[n];
						rgbsum[n].b /= nantialias[n];
					}
				}

				index = j * params.outwidth + i;
				spherical[index].r = blend * rgbsum[0].r + (1 - blend) * rgbsum[1].r;
	        	spherical[index].g = blend * rgbsum[0].g + (1 - blend) * rgbsum[1].g;
	        	spherical[index].b = blend * rgbsum[0].b + (1 - blend) * rgbsum[1].b;
				//printf("%d ", index);

				//printf("\nindex: %d, r: %d, g: %d, b: %d\n", index, spherical[index].r, spherical[index].g, spherical[index].b);

				//if(itable > 100){
					//break;
				//}

			} // i
			//break;
		} // j

		//printf("\nitable: %d\n", itable);
		// Write out the spherical map 
		if (!WriteOutputImage(spherical, basename,fnameout)) {
			fprintf(stderr,"Failed to write output image file\n");
			exit(-1);
		}

	}
	
	Destroy_Bitmap(spherical);
	Destroy_Bitmap(fisheye[0].image);
	Destroy_Bitmap(fisheye[1].image);

	exit(0);

}

void InitParams(void)
{
   time_t secs;
   int seed;

	params.debug = FALSE;
	params.antialias = 2;             // Supersampling antialising
	params.blendmid = 180*DTOR*0.5;   // Mid point for blending
	params.blendwidth = 0;            // Angular blending width
	params.blendpower = 1;
	params.outwidth = 4096;
	params.outheight = 2048;

	// Intensity correction
	// Coefficients of 5th order polynomial brightness correction
   // 1 + a[1]x + a[2]x^2 + a[3]x^3 + a[4]x^4 + a[5]x^5
   // Should map from 0 to 1 to 0 to generally 1+delta
	params.icorrection = FALSE;       // Perform intensity correction or not
	//double ifcn[6] = {0.9998,0.0459,-0.5894,2.4874,-4.2037,2.4599}; // rises to 1.2
	//double ifcn[6] = {1.0,0.1,-1.0417,3.6458,-5.2083,2.6042}; // rises to 1.1
	//double ifcn[6] = {1.0,0.05,-0.5208,1.8229,-2.6042,1.3021}; // rises to 1.05
	params.ifcn[0] = 1.0;
	params.ifcn[1] = 0.1;
	params.ifcn[2] = -1.0417;
	params.ifcn[3] = 3.6458;
	params.ifcn[4] = -5.2083;
	params.ifcn[5] = 2.6042;

	// Experimental optimisation
	params.deltafov = 10*DTOR;        // Variation of fov
	params.deltacenter = 20;          // Variation of fisheye center coordinates
	params.deltatheta = 5*DTOR;       // Variation of rotations

	params.fileformat = TGA;

	// Random number seed
   time(&secs);
   seed = secs;
   //seed = 12345; // Use for constant seed
   srand48(seed);
}

void FlipFisheye(FISHEYE f)
{
	BITMAP4 c1,c2,black = {0,0,0};
	int i,j,x1,y1,x2,y2;
	int index1,index2;

	if (f.hflip < 0) {
		for (i=1;i<=f.radius;i++) {
			for (j=-f.radius;j<=f.radius;j++) {
				x1 = f.centerx-i;
				y1 = f.centery+j;
				x2 = f.centerx+i;
      		y2 = f.centery+j;
				index1 = y1 * f.width + x1;
				index2 = y2 * f.width + x2;

				if (x1 < 0 || y1 < 0 || x1 >= f.width || y1 >= f.height)
					c1 = black;
				else
					c1 = f.image[index1];
            if (x2 < 0 || y2 < 0 || x2 >= f.width || y2 >= f.height)
               c2 = black;
            else
					c2 = f.image[index2];

				if (x1 >= 0 || y1 >= 0 || x1 < f.width || y1 < f.height)
					f.image[index1] = c2;
				if (x2 >= 0 || y2 >= 0 || x2 < f.width || y2 < f.height)
					f.image[index2] = c1;
			}
		}
	}

	if (f.vflip < 0) {
      for (i=-f.radius;i<=f.radius;i++) {
         for (j=1;j<=f.radius;j++) {
            x1 = f.centerx+i;
            y1 = f.centery-j;
            x2 = f.centerx+i;
            y2 = f.centery+j;
            index1 = y1 * f.width + x1;
            index2 = y2 * f.width + x2;

            if (x1 < 0 || y1 < 0 || x1 >= f.width || y1 >= f.height)
               c1 = black;
            else
               c1 = f.image[index1];
            if (x2 < 0 || y2 < 0 || x2 >= f.width || y2 >= f.height)
               c2 = black;
            else
               c2 = f.image[index2];

            if (x1 >= 0 || y1 >= 0 || x1 < f.width || y1 < f.height)
               f.image[index1] = c2;
            if (x2 >= 0 || y2 >= 0 || x2 < f.width || y2 < f.height)
               f.image[index2] = c1;
         }
      }
	}
}

/*
	Read the parameter file, loading up the FISHEYE structure
	Consists of keyword and value pairs, one per line
	This makes lots of assumptions, that is, is not very general and does not deal with edge cases
	Comment lines have # as the first character of the line
*/
int ReadParameters(char *s)
{
	int nfish = 0;
	int i,j,w,h,d,flip;
	char ignore[256],aline[256],fname[256];
	double angle;
	FILE *fptr,*fimg;

   if ((fptr = fopen(s,"r")) == NULL) {
      fprintf(stderr,"   Failed to open parameter file \"%s\"\n",s);
      return(FALSE);
   }
   while (fgets(aline,255,fptr) != NULL) {
      if (aline[0] == '#') // Comment line
         continue;
      if (strstr(aline,"IMAGE:") != NULL) {
		  nfish++;
		  continue;
		  /*
         if (nfish >= 2) {
            fprintf(stderr,"   Already found 2 fisheye images, cannot handle more\n");
            return(FALSE);
         }
			sscanf(aline,"%s %s",ignore,fname);
			if (strlen(fisheye[nfish].fname) > 0)
				strcpy(fname,fisheye[nfish].fname);
			if (IsJPEG(fname))
				params.fileformat = JPG;
			else
				params.fileformat = TGA;
         if ((fimg = fopen(fname,"rb")) == NULL) {
            fprintf(stderr,"   Failed to open image file \"%s\"\n",fname);
            return(FALSE);
         }
			if (params.fileformat == JPG)
				JPEG_Info(fimg,&fisheye[nfish].width,&fisheye[nfish].height,&d);
			else
         	TGA_Info(fimg,&fisheye[nfish].width,&fisheye[nfish].height,&d);
         fisheye[nfish].image = Create_Bitmap(fisheye[nfish].width,fisheye[nfish].height);
   		if (params.fileformat == JPG) {
      		if (JPEG_Read(fimg,fisheye[nfish].image,&w,&h) != 0) {
         		fprintf(stderr,"   Failed to correctly read image \"%s\"\n",fname);
         		return(FALSE);
      		}
   		} else {
         	if (TGA_Read(fimg,fisheye[nfish].image,&w,&h) != 0) {
         	   fprintf(stderr,"   Failed to correctly read image \"%s\"\n",fname);
         	   return(FALSE);
         	}
			}
         fclose(fimg);
			strcpy(fisheye[nfish].fname,fname);
         nfish++;
      
	  	*/
	  }
      if (strstr(aline,"RADIUS:") != NULL && nfish > 0) {
         sscanf(aline,"%s %d",ignore,&i);
         fisheye[nfish-1].radius = i;
      }
      if (strstr(aline,"CENTER:") != NULL && nfish > 0) {
         sscanf(aline,"%s %d %d",ignore,&i,&j);
         fisheye[nfish-1].centerx = i;
         fisheye[nfish-1].centery = j;
      }
      if (strstr(aline,"APERTURE:") != NULL && nfish > 0) { // Historical use, change to FOV
         sscanf(aline,"%s %lf",ignore,&angle);
         fisheye[nfish-1].fov = angle;
      }
      if (strstr(aline,"FOV:") != NULL && nfish > 0) {
         sscanf(aline,"%s %lf",ignore,&angle);
         fisheye[nfish-1].fov = angle;
      }
      if (strstr(aline,"HFLIP:") != NULL && nfish > 0) {
         sscanf(aline,"%s %d",ignore,&flip);
			if (flip < 0)
         	fisheye[nfish-1].hflip = -1;
			else 
				fisheye[nfish-1].hflip = 1;
      }
      if (strstr(aline,"VFLIP:") != NULL && nfish > 0) {
         sscanf(aline,"%s %d",ignore,&flip);
         if (flip < 0)
            fisheye[nfish-1].vflip = -1;
         else 
            fisheye[nfish-1].vflip = 1;
      }
      if (strstr(aline,"ROTATEX:") != NULL && nfish > 0) {
         sscanf(aline,"%s %lf",ignore,&angle);
         fisheye[nfish-1].transform =
            realloc(fisheye[nfish-1].transform,(fisheye[nfish-1].ntransform+1)*sizeof(TRANSFORM));
         fisheye[nfish-1].transform[fisheye[nfish-1].ntransform].axis = XTILT;
         fisheye[nfish-1].transform[fisheye[nfish-1].ntransform].value = DTOR*angle;
         fisheye[nfish-1].ntransform++;
      }
      if (strstr(aline,"ROTATEY:") != NULL && nfish > 0) {
         sscanf(aline,"%s %lf",ignore,&angle);
         fisheye[nfish-1].transform =
            realloc(fisheye[nfish-1].transform,(fisheye[nfish-1].ntransform+1)*sizeof(TRANSFORM));
         fisheye[nfish-1].transform[fisheye[nfish-1].ntransform].axis = YROLL;
         fisheye[nfish-1].transform[fisheye[nfish-1].ntransform].value = DTOR*angle;
         fisheye[nfish-1].ntransform++;
      }
      if (strstr(aline,"ROTATEZ:") != NULL && nfish > 0) {
         sscanf(aline,"%s %lf",ignore,&angle);
         fisheye[nfish-1].transform =
            realloc(fisheye[nfish-1].transform,(fisheye[nfish-1].ntransform+1)*sizeof(TRANSFORM));
         fisheye[nfish-1].transform[fisheye[nfish-1].ntransform].axis = ZPAN;
         fisheye[nfish-1].transform[fisheye[nfish-1].ntransform].value = DTOR*angle;
         fisheye[nfish-1].ntransform++;
      }
   }
	fclose(fptr);

	// Need to have found 2
   if (nfish != 2) {
      fprintf(stderr,"Expected two fisheye images, only found %d\n",nfish);
      return(FALSE);
   }

	return(TRUE);
}

/*
	Set default values for fisheye structure
*/
void InitFisheye(FISHEYE *f)
{
   f->fname[0] = '\0';
   f->image = NULL;
   f->width = 0;
   f->height = 0;
   f->centerx = -1;
   f->centery = -1;
   f->radius = -1;
   f->fov = 180;
	f->hflip = 1;
	f->vflip = 1;
   f->transform = NULL;
   f->ntransform = 0;
}

/*
	Fill in remaining fisheye values
*/
void FisheyeDefaults(FISHEYE *f)
{
	int j;
   /*printf("fov: %lf", f->fov);
   printf("fov: %lf", f->fov/2);
   printf("fov: %lf", DTOR);
   printf("fov: %lf %lf p:%lf", (f->fov/2)*DTOR, 95.0*0.017453, (PI/180));*/
	// fov will only be used as half value, and radians
   f->fov /= 2;    

   f->fov *= DTOR; 

	// Set center to image center, if not set in parameter file
   if (f->centerx < 0 || f->centery < 0) {
      f->centerx = f->width / 2;
      f->centery = f->height / 2;
   }

	// Origin bottom left
   f->centery = f->height - 1 - f->centery;

	// Set fisheye radius to half height, if not set in parameter file
   if (f->radius < 0)
      f->radius = f->height / 2;

   // Precompute sine and cosine of transformation angles
   for (j=0;j<f->ntransform;j++) {
      f->transform[j].cvalue = cos(f->transform[j].value);
      f->transform[j].svalue = sin(f->transform[j].value);
   }
}


int WriteOutputImage(BITMAP4 *spherical, char *basename,char *s)
{
	int i;
	FILE *fptr;
	char fname[256];

	if (IsJPEG(s)) { // remove extension
		for (i=strlen(s)-1;i>0;i--) {
			if (s[i] == '.') {
				s[i] = '\0';
				break;
			}
		}
	}
	strcpy(fname,s);

	// Add extension
	strcat(fname,".jpg");
	// Open file
   if ((fptr = fopen(fname,"wb")) == NULL) {
      fprintf(stderr,"Failed to open output file \"%s\"\n",fname);
      return(FALSE);
   }

    JPEG_Write(fptr,spherical,params.outwidth,params.outheight,100);

   fclose(fptr);
	return(TRUE);
}

/*
	Check that the filename template has the correct number of %d entries
*/
int CheckTemplate(char *s,int nexpect)
{
	int i,n=0;

	for (i=0;i<strlen(s);i++) {
		if (s[i] == '%'){
			n++;
		}
	}

	if (n != nexpect) {
		fprintf(stderr,"This filename template \"%s\" does not look like it contains sufficient %%d entries\n",s);
		fprintf(stderr,"Expect %d but found %d\n",nexpect,n);
		return(FALSE);
	}

	return(TRUE);
}

/*
	Check the frames
	- do they exist
	- are they jpeg
	- are they the same size
	- determine which frame template we are using
*/
int CheckFrames(char *fname1,char *fname2,int *width,int *height)
{
	int i,n=-1;
	int w1,h1,w2,h2,depth;
	FILE *fptr;

   if (!IsJPEG(fname1) || !IsJPEG(fname2)) {
      fprintf(stderr,"CheckFrames() - frame name does not look like a jpeg file\n");
      return(-1);
   }

   // Frame 1
   if ((fptr = fopen(fname1,"rb")) == NULL) {
      fprintf(stderr,"CheckFrames() - Failed to open first frame \"%s\"\n",fname1);
      return(-1);
   }
   JPEG_Info(fptr,&w1,&h1,&depth);
   fclose(fptr);

	// Frame 2
   if ((fptr = fopen(fname2,"rb")) == NULL) {
      fprintf(stderr,"CheckFrames() - Failed to open second frame \"%s\"\n",fname2);
      return(-1);
   }
   JPEG_Info(fptr,&w2,&h2,&depth);
   fclose(fptr);

	// Are they the same size
   if (w1 != w2 || h1 != h2) {
      fprintf(stderr,"CheckFrames() - Frame sizes don't match, %d != %d or %d != %d\n",w1,h1,w2,h2);
      return(-1);
   }
	
	// Is it a known template?
	for (i=0;i<NTEMPLATE;i++) {
		//printf("\n template[i].width: %d, w1: %d, template[i].heigh: %d, h1: %d\n", template[i].width, w1, template[i].height, h1);
		if (w1 == template[i].width && h1 == template[i].height) {
			n = i;
			break;
		}
	}
	if (n < 0) {
		fprintf(stderr,"CheckFrames() - No recognised frame template\n");
		return(-1);
	}

	*width = w1;
	*height = h1;

	return(n);
}
