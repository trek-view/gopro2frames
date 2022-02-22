CC = gcc
CFLAGS = -Wall -O3 
INCLUDES =
LFLAGS = 
LIBS = -ljpeg -lm 

OBJS = fusion2spherebatch.o bitmaplib.o

all: fusion2spherebatch

fusion2spherebatch: $(OBJS)
	$(CC) $(INCLUDES) $(CFLAGS) -o fusion2spherebatch $(OBJS) $(LFLAGS) $(LIBS)

fusion2spherebatch.o: fusion2spherebatch.c fusion2spherebatch.h
	$(CC) $(INCLUDES) $(CFLAGS) -c fusion2spherebatch.c
 
bitmaplib.o: bitmaplib.c bitmaplib.h
	$(CC) $(INCLUDES) $(CFLAGS) -c bitmaplib.c

clean:
	rm -rf core fusion2spherebatch $(OBJS) 
