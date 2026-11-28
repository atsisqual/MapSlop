/* Original synthetic GL fixture for RenderDoc, no external game or map. */
#define GL_GLEXT_PROTOTYPES
#include <SDL2/SDL.h>
#include <GL/gl.h>
#include <dlfcn.h>
#include <stdio.h>
#include "renderdoc_app.h"
int main(int argc,char**argv){
 if(argc!=2||SDL_Init(SDL_INIT_VIDEO))return 1;
 SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION,3);SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION,3);
 SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK,SDL_GL_CONTEXT_PROFILE_CORE);
 SDL_Window*w=SDL_CreateWindow("MapSlop synthetic RenderDoc fixture",0,0,320,240,SDL_WINDOW_OPENGL);
 if(!w)return 2;
 SDL_GLContext ctx=SDL_GL_CreateContext(w);if(!ctx)return 3;
 pRENDERDOC_GetAPI get=(pRENDERDOC_GetAPI)dlsym(RTLD_DEFAULT,"RENDERDOC_GetAPI");
 RENDERDOC_API_1_1_2*api=NULL;if(!get||!get(eRENDERDOC_API_Version_1_1_2,(void**)&api))return 4;
 api->SetCaptureFilePathTemplate(argv[1]);
 const char*vs="#version 330 core\nvoid main(){vec2 p[3]=vec2[3](vec2(-.7,-.7),vec2(.7,-.7),vec2(0,.7));gl_Position=vec4(p[gl_VertexID],0,1);}";
 const char*fs="#version 330 core\nout vec4 c;void main(){c=vec4(.2,.7,.5,1);}";
 GLuint v=glCreateShader(GL_VERTEX_SHADER),f=glCreateShader(GL_FRAGMENT_SHADER);
 glShaderSource(v,1,&vs,0);glCompileShader(v);glShaderSource(f,1,&fs,0);glCompileShader(f);
 GLuint p=glCreateProgram();glAttachShader(p,v);glAttachShader(p,f);glLinkProgram(p);GLint ok;glGetProgramiv(p,GL_LINK_STATUS,&ok);if(!ok)return 5;
 GLuint vao;glGenVertexArrays(1,&vao);glBindVertexArray(vao);glUseProgram(p);
 SDL_GL_SwapWindow(w);api->StartFrameCapture(NULL,NULL);
 glViewport(0,0,320,240);glClearColor(.1,.1,.1,1);glClear(GL_COLOR_BUFFER_BIT);glDrawArrays(GL_TRIANGLES,0,3);glFinish();SDL_GL_SwapWindow(w);
 if(!api->EndFrameCapture(NULL,NULL))return 6;
 SDL_GL_DeleteContext(ctx);SDL_DestroyWindow(w);SDL_Quit();return 0;
}
