(DEFUN Import-Geometry (inpane geom-type &optional here (filter 0) path)
   (LET (bad-thin bad-unclosed bsection cesec ceroof geom  nvertices pane piter points pset roof 
          secname simple-shapes simpleshape surfs type name uniqname vertices viter withholes zone wins 
          nparts surfs-list allwithholes allcorners origin
          (types (case geom-type
                   (building-body
                     '(:cad3d :*))
                   (zone
                     '(:cad3d :exp :*))))
          (building (object inpane))
          *delay-queue*)   
      (setq pane (if here
                    (floor-plan-pane building t t)
                    inpane))
      (when (not pane)
         (return-from import-geometry))
      (if path
         (setf type (length types))
         (multiple-value-setq (path type)
           (ask-for-existing-file :import-cad
             :allowed-types types
             :host 'cad
             :filter filter)))
      (when path
         (when (= type (length types))
            (setq type (file-type-from-extension (pathname-type path) types)))
         (case type
           (1  ;; import inner shell geometry
            (let-if ((vtk (ice-3d-pane building t t)))
              (VtkFlattenDwg (vtk-handle vtk) 0)
              (setf geom (cond ((eq here 1)
                                (ice-add-pict-file vtk path nil building nil))
                               ((eq here 2)
                                (ice-add-pict-file vtk path t building nil))
                               ((consp here)
                                (ice-add-pict-file vtk path here building nil))
                               (t
                                 (ice-add-pict-file vtk path
                                   (list nil nil (get-value building '(defaults current_floor_level)))
                                    building nil))))
              (VtkFlattenDwg (vtk-handle vtk) 1)
              (when geom
                (with-group-delay (building)
                 (setf nparts (VtkGetNSurfaceParts (vtk-handle vtk) #.vtk_3ds 
                                (get-stream-varname vtk :vtk-3ds geom)))
                 (for i from 0 below nparts do
                   (Setlengthunitcoef) 
                   (multiple-value-setq (points nvertices vertices) 
                     (vtk-get-surfaces vtk #.vtk_3ds 
                       (get-stream-varname vtk :vtk-3ds geom) i))
                   (MULTIPLE-VALUE-SETQ(surfs withholes)
                     (NumArrays2Polygons vertices nvertices points))
                   (PUSH surfs surfs-list)
                   (PUSH withholes allwithholes)
                   (SETF allcorners (APPEND allcorners (APPLY #'APPEND surfs)))
                   ) ;; end FOR nparts
                 (vtk-remove-picture pane geom)
                 (del-component (parent geom) geom)
                 (SETF origin (if (consp here) '(0 0 0) (CAR (Maxmin-Corners3d allcorners)))
                       surfs-list (REVERSE surfs-list)
                       allwithholes (REVERSE allwithholes))
                 ;;(Show-Polygons3d-Proj (APPLY #'APPEND surfs-list) "debug-skp")
                 (FOR srfs IN surfs-list AND wh IN allwithholes 
                    WHEN (AND (OR (Length> srfs 3) ;; at least 4 surfaces
                                          (AND  (PUSH srfs bad-unclosed) NIL))
                                       (OR  (>  (* 2 (Polygon-Halfwidth (APPLY #'APPEND srfs))) *minwidth*) ;; not a narrow object with width < 0.5 m
                                             (AND  (PUSH srfs bad-thin) NIL))
                                       )
                   DO
                   (Setlengthunitcoef) 
                   (SETF uniqname (get-unique-component-name (PATHNAME-NAME path) building :doc))
                   (SETF pset (Polyhedron-Withholes srfs wh :mergeplanes T)) 
                   (case geom-type
                     (building-body
                       (MULTIPLE-VALUE-SETQ(bsection roof)
                         (Surfaces-to-Building-Section-G srfs wh *floormaxangle* *wallmaxangle* :name uniqname :origin origin :pset pset))
                       (UNLESS bsection (RETURN-FROM Import-Geometry))
                       (UNLESS roof (Lform-Set-Attributes bsection :n uniqname))
                       (SETF cesec (Make-Component building bsection NIL))
                       (COND 
                             (roof ;; unprotected
                               (do-delayed)
                               (Update-Components cesec roof building NIL)
                               (do-delayed)
                               (SETF ceroof (Find-SubObject "roof" cesec))
                               (Ice-Roof-Invoke ceroof)
                               (do-delayed t))
                             (T ;; protected
                               (Recalculate-Faces cesec)
                               (ice-update-adjacency cesec)
                               (do-delayed)
                               )
                             )
                       ) ;; endcase building-body
                     
                     (zone
                       ;;(SETF srfs (Torus-Polygons 100 5.0 20.0)) 
                        (multiple-value-bind (template name)
                           (ask-for-zone-defaults (object pane) uniqname)
                          (IF wh
                             (MULTIPLE-VALUE-SETQ(bsection zone)
                               (Surfaces-To-Zone-G srfs wh origin 'ce-zone 'zone  :pset pset))
                             (MULTIPLE-VALUE-SETQ(bsection zone simpleshape)
                               (Surfaces-To-Zone srfs origin 'ce-zone 'zone :name name :pset pset))
                             ) ;; end IF
                          (WHEN zone
                             (lform-set-attributes zone :n name)
                             (SETF zone (Make-component building zone nil)
                                   secname (Concatenate-Strings name "-s"))
                             (use-zone-template zone template))
                          )
                        (WHEN zone
                              (COND 
                                         (simpleshape
                                            (MULTIPLE-VALUE-SETQ(bsection roof)
                                                (Surfaces-to-Building-Section-G srfs wh *floormaxangle* *wallmaxangle* :name secname :origin origin :pset pset))
                                            (UNLESS bsection (RETURN-FROM Import-Geometry))
                                            (UNLESS roof (Lform-Set-Attributes bsection :n secname))
                                            ) ;; endcase simpleshape
                                         (T 
                                            (SETF roof NIL)
                                            (Lform-Set-Attributes bsection :n secname)
                                            )
                                         ) ;; end COND             
                              (SETF cesec (Make-Component building bsection NIL))
                              (do-delayed)
                              (Update-Components cesec roof building NIL)
                              (do-delayed)
                              ;:(tracept6 'cesec bsection  cesec roof)
                              (WHEN roof
                                    (SETF ceroof (Find-SubObject "roof" cesec))
                                    (Ice-Roof-Invoke ceroof)
                                    (do-delayed t)
                                    ) ;; end WHEN roof                                   
                              (enclose_zone zone)
                              (do-delayed)
                              (add-object pane (make-zone-frame (get-slot zone 'geometry) (name zone) -1e20 1e20)
                                 :given-shape t)
                              (Recalculate-Faces cesec)
                              (Zone-2-Section-Adjacency zone cesec)
                              (WHEN simpleshape (PUSH (Name zone) simple-shapes))   
                              (do-delayed t)
                              )
                       )
                     ))
                 (WHEN bad-unclosed
                       (Error-Message NIL "~S components were ignored as they have less then 4 surfaces" (LENGTH  bad-unclosed)))
                 (WHEN bad-thin
                       (Error-Message NIL "~S components were ignored as their width is less then ~A m" (LENGTH  bad-thin) *minwidth*))
                 (case geom-type
                   (zone
                     (calculate-ext-adjacency building)
                     (for z in (:zones building) do (calculate-adjacency z))
                     (for z in (:zones building) do (ice-on-zone-size z))
                      (WHEN (MEMBER (Name zone) simple-shapes :test #'STRING-EQUAL) (Zone-To-Simple zone))
                      ))
                 (set-stream-prop vtk :refresh-reset t)))
              (update-pane pane))
            (return-from import-geometry))
           (2  ;; *.exp geometry
            (let-if ((vtk (ice-3d-pane building t t)))
              (import-exp-model vtk path)
              (get-exp-windows vtk)
              (update-pane pane))
            (return-from import-geometry))
           (3
            (pop-up-message :unsupported-file nil (file-namestring path))
            (return-from import-geometry))))
      ))