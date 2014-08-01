#ifdef HAVE_PP
#include "cdunifpp.h"

/* store any variables controlled by the environment */
int pp_set_vars_from_env(PPfile *ppfile)
{
  char *val;
  val = getenv("RAW_PP_HDR");
  if (val && strlen(val) > 0) {
    ppfile->store_raw_headers = 1;
  }
  val = getenv("PP_BASETIME");
  if (val && strcmp(val,"model")==0) {
    ppfile->basetime = 1;
  }
}

#endif
