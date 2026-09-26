import{c as i}from"./index-DwPqhDl8.js";import{r as c}from"./react-C0lScGWE.js";import{f as u}from"./data-CitRxYzG.js";/**
 * @license lucide-react v0.453.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const m=i("CircleCheck",[["circle",{cx:"12",cy:"12",r:"10",key:"1mglay"}],["path",{d:"m9 12 2 2 4-4",key:"dzmm74"}]]);/**
 * @license lucide-react v0.453.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const h=i("TriangleAlert",[["path",{d:"m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3",key:"wmoenq"}],["path",{d:"M12 9v4",key:"juzpu7"}],["path",{d:"M12 17h.01",key:"p32p05"}]]),o=10*60*1e3;function a(e,t,n=o){return!e||!t?!1:t-e>=n}function l(e,t=o){c.useEffect(()=>{if(typeof document>"u")return;let n=0;const r=()=>{if(document.hidden){n=Date.now();return}a(n,Date.now(),t)&&(n=0,u(!0).then(e).catch(()=>{}))};return document.addEventListener("visibilitychange",r),window.addEventListener("focus",r),()=>{document.removeEventListener("visibilitychange",r),window.removeEventListener("focus",r)}},[e,t])}export{m as C,h as T,l as u};
