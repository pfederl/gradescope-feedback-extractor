SRCS=$(wildcard outputs/t*.html)

$(info $$SRCS is [${SRCS}])


OBJS=$(SRCS:.html=.pdf)

all: $(OBJS)

%.pdf : %.html
	@echo Converting $< to $@
	wkhtmltopdf -s Letter -L 0.5in -R 0.5in -B 0.5in -T 0.5in $< $@



