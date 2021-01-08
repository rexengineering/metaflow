The JSON data in this subdirectory was generated from a Node session similar to
the following:

```javascript
// Requires npm install of "bpmn-moddle"
var bpmnModdle
import('bpmn-moddle').then(module => { bpmnModdle = new module.default() })
const fs = require('fs')
const specs = ['dc', 'di', 'bioc', 'bpmndi', 'bpmn']
for (let idx in specs) {
    let spec_name = specs[idx];
    fs.writeSync(
        fs.openSync(`${spec_name}.json`, 'w'),
        JSON.stringify(bpmnModdle.registry.packageMap[spec_name])
    )
}
```
