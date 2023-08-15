```{mermaid}
:alt: Data process graph
:caption: Data process graph
flowchart TD
 node2["data\rois.dvc"]
 node3["data\sources.dvc"]
 node4["fill"]
 node5["find_contours"]
 node8["preview_binarized"]
 node9["preview_filled"]
 node10["preview_gray"]
 node11["data\examples.dvc"]
 node12["data\samples.dvc"]
 node2-->node8
 node3-->node4
 node3-->node5
 node3-->node8
 node3-->node9
 node3-->node10
 node4-->node9
 node5-->node4
```
